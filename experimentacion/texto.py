import os
import shutil
import time
from typing import List, Tuple

import pandas as pd

from Indice_invertido.invertido_indice import CustomInvertedIndex

# Configuración
CSV_FILE = "./Indice_invertido/dataset/musica.csv"
N_VALUES = [2000, 4000, 8000, 16000, 32000]
QUERY_TEXT = "amor & guerra"
TOP_K = 10


def cargar_dataset() -> pd.DataFrame:
    df = pd.read_csv(CSV_FILE)
    columnas_necesarias = ["lyrics", "track_name", "track_artist", "playlist_genre"]
    faltantes = [c for c in columnas_necesarias if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias en el CSV: {faltantes}")
    return df


def expandir_dataset(base: pd.DataFrame, n: int) -> pd.DataFrame:
    if len(base) >= n:
        subset = base.iloc[:n].copy().reset_index(drop=True)
    else:
        copias: List[pd.DataFrame] = []
        restante = n
        while restante > 0:
            bloque = base.iloc[: min(len(base), restante)].copy()
            copias.append(bloque)
            restante -= len(bloque)
        subset = pd.concat(copias, ignore_index=True)

    subset.insert(0, "doc_id", range(1, len(subset) + 1))
    return subset


def ejecutar_experimento(df_base: pd.DataFrame) -> List[Tuple[int, float, List[str], bool]]:
    resultados = []
    baseline_top: List[str] = []

    for n in N_VALUES:
        df_n = expandir_dataset(df_base, n)
        indice_path = os.path.join(os.path.dirname(__file__), "dataset", f"inverted_index_{n}")

        if os.path.exists(indice_path):
            shutil.rmtree(indice_path)

        index = CustomInvertedIndex(
            dataframe=df_n,
            columns={
                "id": "doc_id",
                "text": ["lyrics", "track_name", "track_artist", "playlist_genre"],
            },
            index_path=indice_path,
        )

        index.build_index()
        top_docs, tiempo = index.search(QUERY_TEXT, top_k=TOP_K, fields=["lyrics"])
        doc_ids = [str(doc) for doc, _ in top_docs]

        if not baseline_top:
            baseline_top = doc_ids
            coincide = True
        else:
            coincide = doc_ids == baseline_top

        resultados.append((n, tiempo, doc_ids, coincide))

    return resultados


def main():
    print("\n=== Experimento: Índice invertido propio ===")
    print(f"Consulta utilizada: '{QUERY_TEXT}' (campos: lyrics)")
    print("N | Tiempo de respuesta (s) | Coincide con N=2000 | Top IDs")
    print("-" * 80)

    base_df = cargar_dataset()
    resultados = ejecutar_experimento(base_df)

    for n, tiempo, top_ids, coincide in resultados:
        etiqueta_coincide = "Sí" if coincide else "No"
        print(f"{n:<6} | {tiempo:>22.6f} | {etiqueta_coincide:^19} | {', '.join(top_ids)}")


if __name__ == "__main__":
    main()