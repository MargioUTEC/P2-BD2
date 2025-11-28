"""
test_metadata_query.py
----------------------

Script de prueba manual para el motor de consultas de metadata.

Objetivos:
- Verificar que:
    - metadata.db existe y es accesible
    - ParserSQL funciona (grammar_sql.lark OK)
    - MetadataQueryEngine construye bien el SQL y devuelve filas
- Probar tanto la forma "corta" (solo condición) como la forma "larga" (SELECT completo).
"""

from pathlib import Path
from pprint import pprint

from audio.config_metadata import SQLITE_DB_PATH
from test_parser.sql.metadata_query_engine import MetadataQueryEngine


def print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def run_single_test(engine: MetadataQueryEngine, query: str, max_rows: int = 5) -> None:
    print_header(f"QUERY DE USUARIO:\n{query!r}")

    try:
        result = engine.run_query(query)
    except Exception as e:
        print("[ERROR] Ocurrió una excepción al ejecutar la consulta:")
        print(repr(e))
        return

    sql = result["sql"]
    params = result["params"]
    rows = result["rows"]

    print("\n[SQL GENERADA]")
    print(sql)
    print("\n[PARÁMETROS]")
    print(params)
    print(f"\n[TOTAL FILAS] {len(rows)}")

    if rows:
        print(f"\n[PRIMERAS {min(max_rows, len(rows))} FILAS]:")
        for i, row in enumerate(rows[:max_rows], start=1):
            print(f"\n--- Fila {i} ---")
            pprint(row)
    else:
        print("\n[INFO] No se encontraron filas para esta consulta.")


def main() -> None:
    print("=== PRUEBA DEL MOTOR DE METADATA ===")

    db_path = Path(SQLITE_DB_PATH)
    print(f"[INFO] Usando base de datos: {db_path}")

    if not db_path.exists():
        print("[ERROR] metadata.db no existe. Asegúrate de haber corrido antes el script")
        print("        que construye la base (build_metadata_sqlite_optimized.py).")
        return

    engine = MetadataQueryEngine(db_path=db_path)

    # --------------------------------------------------------
    # Lista de pruebas recomendadas
    # Ajusta los valores (artistas, géneros, años) según tu dataset.
    # --------------------------------------------------------
    test_queries = [
        # 1) Forma corta: solo condición WHERE
        'artist = "Psychadelik Pedestrian"',
        'genre = "Electronic" AND year >= 2010',
        'year BETWEEN 2010 AND 2015',

        # 2) Forma larga: SELECT completo
        '''
        SELECT track_id, title, artist
        FROM metadata
        WHERE genre = "Electronic" AND year >= 2010
        ''',

        # 3) Búsqueda por track_id (probar normalización a 6 dígitos)
        'track_id = "34996"',   # debería normalizarse a "034996" si existe
    ]

    for q in test_queries:
        run_single_test(engine, q, max_rows=3)


if __name__ == "__main__":
    main()
