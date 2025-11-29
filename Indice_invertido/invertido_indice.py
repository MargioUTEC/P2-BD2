# import pandas as pd
# import nltk
# from nltk.stem.snowball import SnowballStemmer
# from nltk.tokenize import RegexpTokenizer
# from collections import defaultdict
import os
import math
import pickle
import time
from collections import defaultdict
from typing import Iterable, List, Optional, Tuple

import nltk
import pandas as pd
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import RegexpTokenizer

nltk.download('punkt')

class CustomInvertedIndex:
    def __init__(self,
                 dataset_path: Optional[str] = None,
                 dataframe: Optional[pd.DataFrame] = None,
                 columns: dict = None,
                 stoplist_path: Optional[str] = None,
                 index_path: Optional[str] = None,
                 block_limit: int = 500):

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        self.dataset_path = dataset_path or os.path.join(BASE_DIR, "dataset", "musica.csv")
        self.stoplist_path = stoplist_path or os.path.join(BASE_DIR, "dataset", "stoplist.txt")
        self.path = index_path or os.path.join(BASE_DIR, "dataset", "inverted_index")

        columns = columns or {
            'id': 'track_id',
            'text': ['lyrics', 'track_name', 'track_artist', 'playlist_genre']
        }



        self.id_column = columns['id']
        self.text_fields = columns['text']
        self.block_limit = block_limit
        self.stemmer = SnowballStemmer('english')
        self.idf = {}
        self.total_blocks = 0

        # Stoplist
        self.stoplist = set()
        try:
            with open(self.stoplist_path, encoding="utf-8") as f:
                self.stoplist = {line.strip().lower() for line in f}
        except FileNotFoundError:
            print("Stoplist no encontrada, usando vacío.")
        self.stoplist.update(['?', '-', '.', ':', ',', '!', ';', '_'])

        # Cargar dataset
        if dataframe is not None:
            self.data = dataframe.copy()
        else:
            self.data = pd.read_csv(self.dataset_path)

        if self.id_column not in self.data:
            raise ValueError(f"El dataset no contiene la columna de id '{self.id_column}'.")

        self.data.dropna(subset=self.text_fields, inplace=True)
        self.total_docs = len(self.data)

        # Preprocesar dataset
        self.dataset = {}
        for _, row in self.data.iterrows():
            doc_id = row[self.id_column]
            self.dataset[doc_id] = {}
            for field in self.text_fields:
                self.dataset[doc_id][field] = self._preprocess(str(row[field]), field)

        # Crear carpeta índice si no existe
        if not os.path.exists(self.path):
            os.makedirs(self.path)

        self._precalculate_idf()

    def _preprocess(self, text, field):
        text = text.lower()
        tokenizer = RegexpTokenizer(r'\w+')
        words = tokenizer.tokenize(text)
        words = [
            f"{field}:{self.stemmer.stem(word)}"
            for word in words
            if word.isascii() and len(word) >= 2 and word.isalpha() and word not in self.stoplist
        ]
        return words

    def _precalculate_idf(self):
        temp_dict = defaultdict(set)
        for doc_id, fields in self.dataset.items():
            for field, terms in fields.items():
                for term in set(terms):
                    temp_dict[term].add(doc_id)

        for term, docs in temp_dict.items():
            self.idf[term] = math.log10(self.total_docs / len(docs))

    def build_index(self):
        final_index_path = os.path.join(self.path, "final_index.bin")
        if os.path.exists(final_index_path):
            os.remove(final_index_path)
            print("Eliminando índice previo...")

        start = time.time()
        block_dict = defaultdict(dict)
        block_count = 0

        # Construcción SPIMI
        for i, (doc_id, fields) in enumerate(self.dataset.items()):
            for field, words in fields.items():
                for word in words:
                    block_dict[word][doc_id] = block_dict[word].get(doc_id, 0) + 1

            if (i + 1) % self.block_limit == 0:
                self._save_block(block_dict, block_count, temp=True)
                block_dict.clear()
                block_count += 1

        if block_dict:
            self._save_block(block_dict, block_count, temp=True)
            block_count += 1

        self.total_blocks = block_count
        self._merge_all_blocks()
        self._clean_temp_blocks()

        end = time.time()
        print(f"\n SPIMI completado en {end - start:.2f} segundos\n")

        print("Calculando normas (para similitud de coseno)...")

        self.doc_norms = defaultdict(float)

        with open(os.path.join(self.path, "final_index.bin"), "rb") as f:
            index_data = pickle.load(f)

        for term, postings in index_data.items():
            idf = self.idf.get(term, 0)
            for doc_id, freq in postings.items():
                tf = math.log10(1 + freq)
                tfidf = tf * idf
                self.doc_norms[doc_id] += tfidf ** 2

        for doc_id in self.doc_norms:
            self.doc_norms[doc_id] = math.sqrt(self.doc_norms[doc_id])

        with open(os.path.join(self.path, "doc_norms.pkl"), "wb") as nf:
            pickle.dump(dict(self.doc_norms), nf)

        print("Normas calculadas y guardadas!\n")

    def _save_block(self, dictionary, block_id, temp=False):
        sorted_dict = {term: dictionary[term] for term in sorted(dictionary)}
        name = f"temp_block_{block_id}.bin" if temp else f"block_{block_id}.bin"
        with open(os.path.join(self.path, name), "wb") as file:
            pickle.dump(sorted_dict, file)

    def _merge_all_blocks(self):
        print("Fusionando bloques...")
        levels = math.ceil(math.log2(self.total_blocks))
        for level in range(1, levels + 1):
            step = 2 ** level
            for i in range(0, self.total_blocks, step):
                start = i
                finish = min(i + step - 1, self.total_blocks - 1)
                self._merge_blocks(start, finish)

        os.rename(
            os.path.join(self.path, "block_0.bin"),
            os.path.join(self.path, "final_index.bin")
        )
        print("Fusión completa.\n")

    def _merge_blocks(self, start, finish):
        merged = defaultdict(dict)
        for i in range(start, finish + 1):
            fname = os.path.join(self.path, f"temp_block_{i}.bin")
            if os.path.exists(fname):
                with open(fname, "rb") as f:
                    data = pickle.load(f)
                    for term, postings in data.items():
                        for doc_id, freq in postings.items():
                            merged[term][doc_id] = freq

        self._save_block(merged, start)

    def _clean_temp_blocks(self):
        for f in os.listdir(self.path):
            if f.startswith("temp_block_"):
                os.remove(os.path.join(self.path, f))

    def _load_index_from_disk(self):
        index_file = os.path.join(self.path, "final_index.bin")
        norms_file = os.path.join(self.path, "doc_norms.pkl")

        if not os.path.exists(index_file) or not os.path.exists(norms_file):
            raise FileNotFoundError(
                "No se encontró el índice almacenado. Ejecute build_index() antes de buscar."
            )

        with open(index_file, "rb") as f:
            self.index_data = pickle.load(f)

        with open(norms_file, "rb") as f:
            self.doc_norms = pickle.load(f)

    def _preprocess_query(self, query: str, fields: Optional[Iterable[str]] = None) -> List[str]:
        fields = list(fields) if fields else [self.text_fields[0]]
        query = query.lower()
        tokenizer = RegexpTokenizer(r"\w+")
        words = tokenizer.tokenize(query)
        return [
            f"{field}:{self.stemmer.stem(word)}"
            for word in words
            for field in fields
            if word.isascii() and len(word) >= 2 and word.isalpha() and word not in self.stoplist
        ]

    def search(self, query: str, top_k: int = 10, fields: Optional[Iterable[str]] = None) -> Tuple[List[Tuple[str, float]], float]:
        start = time.time()

        if not hasattr(self, "index_data") or not hasattr(self, "doc_norms"):
            self._load_index_from_disk()

        terms = self._preprocess_query(query, fields)
        scores = defaultdict(float)

        for term in terms:
            postings = self.index_data.get(term)
            if not postings:
                continue

            idf = self.idf.get(term, 0)
            for doc_id, freq in postings.items():
                tf = math.log10(1 + freq)
                scores[doc_id] += tf * idf

        results = []
        for doc_id, score in scores.items():
            norm = self.doc_norms.get(doc_id)
            if norm:
                results.append((doc_id, score / norm))

        results.sort(key=lambda x: x[1], reverse=True)
        elapsed = time.time() - start
        return results[:top_k], elapsed



if __name__ == "__main__":
    index = CustomInvertedIndex()
    index.build_index()
    print("Índice generado correctamente")
