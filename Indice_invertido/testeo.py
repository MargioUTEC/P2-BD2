import pickle
import os
from invertido_indice import CustomInvertedIndex
import math

# ===============================================================
# 1. Construir el índice invertido (si no existe)
# ===============================================================

print("\n=== Construyendo índice invertido (SPIMI) ===")

index = CustomInvertedIndex()
index.build_index()

print("Índice invertido construido correctamente.")
print(f"Total de documentos indexados: {index.total_docs}")
print(f"Total de términos en IDF: {len(index.idf)}")


# ===============================================================
# 2. Cargar el índice final desde disco
# ===============================================================

final_index_path = os.path.join(index.path, "final_index.bin")
doc_norms_path   = os.path.join(index.path, "doc_norms.pkl")

print("\n=== Cargando archivos generados ===")

with open(final_index_path, "rb") as f:
    inverted_index = pickle.load(f)

with open(doc_norms_path, "rb") as f:
    doc_norms = pickle.load(f)

print("Índice cargado.")
print(f"Términos totales: {len(inverted_index)}")
print(f"Normas cargadas para {len(doc_norms)} documentos.")


# ===============================================================
# 3. Función para preprocesar consulta
# ===============================================================

def preprocess_query(text):
    text = text.lower()
    tokenizer = index.stemmer
    stoplist = index.stoplist
    words = [w for w in text.split() if w not in stoplist]
    return [f"query:{index.stemmer.stem(w)}" for w in words]


# ===============================================================
# 4. Similitud de coseno
# ===============================================================

def cosine_sim(score, doc_norm):
    if doc_norm == 0:
        return 0
    return score / doc_norm


# ===============================================================
# 5. TEST: Buscar un texto simple
# ===============================================================

query = "love forever dancing"
print("\n=== Consulta de prueba ===")
print("Query:", query)

terms = preprocess_query(query)
print("Términos procesados:", terms)

scores = {}

# scoring
for term in terms:
    if term not in inverted_index:
        continue

    postings = inverted_index[term]
    idf = index.idf.get(term, 0)

    for doc_id, freq in postings.items():
        tf = math.log10(1 + freq)
        tfidf = tf * idf

        scores[doc_id] = scores.get(doc_id, 0) + tfidf


print("\n=== Scores parciales (sin normalizar) ===")
for d, s in list(scores.items())[:5]:
    print(d, s)

# normalizar
results = []
for doc_id, partial_score in scores.items():
    sim = cosine_sim(partial_score, doc_norms.get(doc_id, 1))
    results.append((doc_id, sim))

results.sort(key=lambda x: x[1], reverse=True)

top_k = 10
print(f"\n=== Top-{top_k} documentos más similares ===")
for doc, score in results[:top_k]:
    print(f"Doc {doc} → Score: {score:.4f}")
