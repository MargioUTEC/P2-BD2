"""
test_metadata_query.py
----------------------

Test funcional de alto nivel para MetadataQuery:

1. Carga de metadata parseada y índices invertidos.
2. Construcción de MetadataQuery y B+Tree.
3. Pruebas de:
   - get_by_track_id
   - get_by_genre
   - get_by_artist
   - get_by_year
   - filter(genre, year)
   - enrich_audio_results
"""

import traceback

from metadata.metadata_query import MetadataQuery


def _pick_any_track(mq: MetadataQuery):
    """
    Toma un track_id cualquiera y su metadata asociada.
    """
    tid = next(iter(mq.table.keys()))
    return tid, mq.table[tid]


def test_metadata_query_basic():
    print("\n========== TEST: METADATA QUERY ==========\n")

    # ---------------------------------------------------------
    # 1) Construcción del objeto principal
    # ---------------------------------------------------------
    print("→ Inicializando MetadataQuery...")
    mq = MetadataQuery(build_bptree=True)
    assert len(mq.table) > 0, "❌ La tabla de metadata está vacía."
    print(f"✓ Metadata cargada en memoria. Total tracks: {len(mq.table)}")

    # ---------------------------------------------------------
    # 2) Elegir un track de ejemplo
    # ---------------------------------------------------------
    tid, md = _pick_any_track(mq)
    print(f"→ Usando track_id de ejemplo: {tid}")

    assert "track" in md, "❌ La entrada de metadata no contiene sección 'track'."
    print("✓ Entrada de metadata contiene sección 'track'.")

    # ---------------------------------------------------------
    # 3) get_by_track_id
    # ---------------------------------------------------------
    print("\n→ Probando get_by_track_id...")
    res_by_id = mq.get_by_track_id(tid)
    assert res_by_id is not None, "❌ get_by_track_id devolvió None."
    assert isinstance(res_by_id, dict), "❌ get_by_track_id no devolvió un dict."
    assert "track" in res_by_id, "❌ El resultado de get_by_track_id no tiene 'track'."
    print("✓ get_by_track_id OK.")

    # ---------------------------------------------------------
    # 4) get_by_genre
    # ---------------------------------------------------------
    print("\n→ Probando get_by_genre (si hay géneros disponibles)...")
    track_info = md.get("track", {}) or {}

    # intentamos obtener lista de géneros desde 'genres' o 'genres_all'
    genres = track_info.get("genres") or track_info.get("genres_all")
    genre_top = track_info.get("genre_top")

    if isinstance(genres, list) and len(genres) > 0:
        test_genre = genres[0]
    elif genre_top is not None:
        test_genre = genre_top
    else:
        test_genre = None

    if test_genre is None:
        print("⚠ No se encontró genre_id en este track. Se omite prueba de get_by_genre.")
    else:
        res_genre = mq.get_by_genre(test_genre)
        assert isinstance(res_genre, list), "❌ get_by_genre no devolvió una lista."
        assert len(res_genre) > 0, "❌ get_by_genre devolvió lista vacía."

        # Comprobar que al menos uno de los resultados tiene 'track'
        assert any("track" in r for r in res_genre), "❌ Resultados de get_by_genre sin sección 'track'."
        print(f"✓ get_by_genre({test_genre}) OK. Resultados: {len(res_genre)}")

    # ---------------------------------------------------------
    # 5) get_by_artist
    # ---------------------------------------------------------
    print("\n→ Probando get_by_artist (si hay artist_id disponible)...")
    artist_info = md.get("artist", {}) or {}
    artist_id = artist_info.get("id") or artist_info.get("artist_id")

    if artist_id is None:
        print("⚠ No se encontró artist_id en este track. Se omite prueba de get_by_artist.")
    else:
        res_artist = mq.get_by_artist(artist_id)
        assert isinstance(res_artist, list), "❌ get_by_artist no devolvió una lista."
        assert len(res_artist) > 0, "❌ get_by_artist devolvió lista vacía."
        print(f"✓ get_by_artist({artist_id}) OK. Resultados: {len(res_artist)}")

    # ---------------------------------------------------------
    # 6) get_by_year
    # ---------------------------------------------------------
    print("\n→ Probando get_by_year (si hay año deducible)...")
    date_released = track_info.get("date_released")
    date_created = track_info.get("date_created")

    year_val = None
    for d in (date_released, date_created):
        if isinstance(d, str) and len(d) >= 4 and d[:4].isdigit():
            year_val = int(d[:4])
            break

    if year_val is None:
        print("⚠ No se pudo extraer año de este track. Se omite prueba de get_by_year.")
    else:
        res_year = mq.get_by_year(year_val)
        assert isinstance(res_year, list), "❌ get_by_year no devolvió una lista."
        assert len(res_year) > 0, "❌ get_by_year devolvió lista vacía."
        print(f"✓ get_by_year({year_val}) OK. Resultados: {len(res_year)}")

    # ---------------------------------------------------------
    # 7) filter(genre, year) combinado
    # ---------------------------------------------------------
    if test_genre is not None and year_val is not None:
        print("\n→ Probando filter(genre, year) combinado...")
        res_filter = mq.filter(genre=test_genre, year=year_val)
        assert isinstance(res_filter, list), "❌ filter no devolvió una lista."
        # Puede ser una lista pequeña, pero no debería romper
        print(f"✓ filter(genre={test_genre}, year={year_val}) OK. Resultados: {len(res_filter)}")
    else:
        print("\n⚠ No se puede probar filter(genre, year) porque falta genre o year para el track de ejemplo.")

    # ---------------------------------------------------------
    # 8) enrich_audio_results
    # ---------------------------------------------------------
    print("\n→ Probando enrich_audio_results...")
    audio_results = [(tid, 0.99)]
    enriched = mq.enrich_audio_results(audio_results)

    assert isinstance(enriched, list), "❌ enrich_audio_results no devolvió una lista."
    assert len(enriched) == 1, "❌ enrich_audio_results debería devolver exactamente un resultado."
    item = enriched[0]

    assert item.get("track_id") == str(tid), "❌ track_id incorrecto en enrich_audio_results."
    assert abs(item.get("score", 0.0) - 0.99) < 1e-6, "❌ score incorrecto en enrich_audio_results."
    # No exigimos que siempre haya título/artista/género, pero al menos las claves existen
    for field in ("title", "artist", "genre", "year"):
        assert field in item, f"❌ Falta campo '{field}' en enrich_audio_results."

    print("✓ enrich_audio_results OK.")

    print("\n🎉 TEST DE METADATA_QUERY SUPERADO CON ÉXITO.\n")


if __name__ == "__main__":
    # Permite correr el test como script:
    #   python -m tests.test_metadata_query
    try:
        test_metadata_query_basic()
    except AssertionError as e:
        print("\n[ASSERTION FAILED]")
        print(e)
        traceback.print_exc()
        raise
    except Exception as e:
        print("\n[UNEXPECTED ERROR]")
        print(e)
        traceback.print_exc()
        raise
