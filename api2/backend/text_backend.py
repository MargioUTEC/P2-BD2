# api2/backend/text_backend.py

import os
import time
import pickle
import pandas as pd
import math

from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import RegexpTokenizer


class TextSearchBackend:
    def __init__(self, base_index_dir: str):
        """
        base_index_dir = Ruta donde está:
            - musica.csv
            - stoplist.txt
            - inverted_index/final_index.bin
            - inverted_index/doc_norms.pkl
        """

        self.base_dir = base_index_dir

        # -----------------------------
        # Paths
        # -----------------------------
        self.csv_path = os.path.join(base_index_dir, "musica.csv")
        self.stoplist_path = os.path.join(base_index_dir, "stoplist.txt")
        self.index_path = os.path.join(base_index_dir, "inverted_index", "final_index.bin")
        self.norms_path = os.path.join(base_index_dir, "inverted_index", "doc_norms.pkl")

        # -----------------------------
        # Validación de archivos
        # -----------------------------
        if not os.path.exists(self.index_path):
            raise RuntimeError("Índice invertido no encontrado. Debes construirlo primero.")

        if not os.path.exists(self.csv_path):
            raise RuntimeError(f"No se encontró musica.csv en: {self.csv_path}")

        # -----------------------------
        # Cargar CSV completo
        # -----------------------------
        self.data = pd.read_csv(self.csv_path)
        self.data.set_index("track_id", inplace=True)

        # -----------------------------
        # Cargar índice invertido
        # -----------------------------
        with open(self.index_path, "rb") as f:
            self.index = pickle.load(f)

        # -----------------------------
        # Cargar normas
        # -----------------------------
        with open(self.norms_path, "rb") as f:
            self.doc_norms = pickle.load(f)

        # -----------------------------
        # Preprocesamiento para consultas
        # -----------------------------
        self.tokenizer = RegexpTokenizer(r'\w+')
        self.stemmer = SnowballStemmer('english')

        # Cargar stoplist
        self.stoplist = set()
        if os.path.exists(self.stoplist_path):
            with open(self.stoplist_path, encoding="utf-8") as f:
                for w in f:
                    self.stoplist.add(w.strip().lower())

        self.stoplist.update(["?", "-", ".", ",", ":", "!", ";", "_"])

        print("Backend de texto inicializado correctamente.")

    # --------------------------------------------------------------------
    # Preprocesamiento de consultas
    # --------------------------------------------------------------------
    def preprocess_query(self, query: str):
        words = self.tokenizer.tokenize(query.lower())
        clean = [
            self.stemmer.stem(w)
            for w in words
            if w.isascii() and len(w) >= 2 and w.isalpha() and w not in self.stoplist
        ]
        return clean

    # --------------------------------------------------------------------
    # Búsqueda por similitud coseno
    # --------------------------------------------------------------------
    def search(self, query: str, top_k: int = 5):
        t0 = time.time()

        terms = self.preprocess_query(query)
        if not terms:
            return []

        # ------------------------
        # Score coseno
        # ------------------------
        scores = {}

        for stem in terms:
            # debe buscar en todos los prefijos <campo>:<stem>
            for term in list(self.index.keys()):
                if term.endswith(stem):  # ej: lyrics:love
                    postings = self.index[term]
                    for doc_id, freq in postings.items():
                        tf = math.log10(1 + freq)
                        scores[doc_id] = scores.get(doc_id, 0) + tf

        # Normalizar por norma
        for doc_id in list(scores.keys()):
            norm = self.doc_norms.get(doc_id, 1)
            scores[doc_id] /= norm

        # Ranking
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        elapsed = (time.time() - t0) * 1000  # ms

        results = []
        for doc_id, score in ranked:
            row = self.data.loc[doc_id]

            lyrics_excerpt = str(row["lyrics"])[:200].replace("\n", " ")

            results.append({
                "track_id": doc_id,
                "score": float(score),
                "title": row["track_name"],
                "artist": row["track_artist"],
                "lyrics_excerpt": lyrics_excerpt,
                "genre": row["playlist_genre"],
                "album": row["track_album_name"],
                "playlist": row["playlist_name"],
                "elapsed_ms": elapsed,
            })

        return results
