import psycopg2
import csv
import time
import os

# 1. Ruta de tu archivo real
CSV_FILE = "./Indice_invertido/dataset/musica.csv"

# 2. ESCALA DE 'N' (Según lo que aprobó el profe: 2k, 4k, 8k, 16k, 32k)
N_VALUES = [2000, 4000, 8000, 16000, 32000]

# 3. TIPO DE ÍNDICE ("GIN" y "GIST")
TIPO_INDICE = "GIST"  

# 4. Conexión a tu Docker
DB_CONFIG = {
    "host": "localhost", "port": "5433", 
    "user": "dianananez", "password": "proyecto2bd", "dbname": "multimedia_db"
}


def conectar():
    return psycopg2.connect(**DB_CONFIG)

def main():
    print(f"\nINICIANDO EXPERIMENTO PSQL DE TEXTO")
    print(f"Índice seleccionado: {TIPO_INDICE}")
    print("=" * 60)

    # 1. CARGAR DATOS A MEMORIA
    datos_memoria = []
    try:
        print("Leyendo CSV...")
        with open(CSV_FILE, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Aseguramos que existan las columnas (ajusta si tus cabeceras son distintas)
                track = row.get('track_name', row.get('song_name', ''))
                artist = row.get('artist_name', row.get('artist', ''))
                lyrics = row.get('lyrics', row.get('text', ''))
                if lyrics: 
                    datos_memoria.append((track, artist, lyrics))
    except Exception as e:
        print(f"Error leyendo CSV: {e}")
        return

    print(f"Canciones reales cargadas: {len(datos_memoria)}")
    
    # CLONACIÓN AUTOMÁTICA
    MAX_N = max(N_VALUES)
    while len(datos_memoria) < MAX_N:
        print(f"Faltan datos para llegar a {MAX_N}. Duplicando dataset...")
        datos_memoria += datos_memoria
    
    print(f"Total datos listos para prueba: {len(datos_memoria)}")
    print("-" * 60)
    print(f"{'N (Cantidad)':<15} | {'Tiempo Búsqueda (s)':<20} | {'Resultados'}")
    print("-" * 60)

    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor()

    # --- 2. BUCLE DEL EXPERIMENTO ---
    for n in N_VALUES:
        # A. Empezar de cero para este N
        cur.execute("DROP TABLE IF EXISTS experimento_texto;")
        cur.execute("""
            CREATE TABLE experimento_texto (
                id SERIAL PRIMARY KEY,
                track_name TEXT,
                artist_name TEXT,
                lyrics TEXT
            );
        """)
        
        # B. Insertar N registros (usando mogrify para velocidad)
        batch = datos_memoria[:n]
        args = ','.join(cur.mogrify("(%s,%s,%s)", x).decode('utf-8') for x in batch)
        cur.execute("INSERT INTO experimento_texto (track_name, artist_name, lyrics) VALUES " + args)
        
        # C. Crear el Índice (GIN o GIST)
        # 'spanish' optimiza la búsqueda para nuestro idioma
        cur.execute(f"CREATE INDEX idx_lyrics_gist ON experimento_texto USING {TIPO_INDICE} (to_tsvector('spanish', lyrics));")
        
        # D. Medir Búsqueda (Promedio de 5 intentos)
        consulta = "amor & guerra" # Buscamos canciones que tengan ambas palabras
        tiempos = []
        for _ in range(5):
            t0 = time.time()
            cur.execute(f"""
                SELECT track_name FROM experimento_texto 
                WHERE to_tsvector('spanish', lyrics) @@ to_tsquery('spanish', '{consulta}')
                LIMIT 10;
            """)
            cur.fetchall()
            t1 = time.time()
            tiempos.append(t1 - t0)
        
        promedio = sum(tiempos) / len(tiempos)
        
        print(f"{n:<15} | {promedio:.6f}             | {len(batch)}")

    cur.close()
    conn.close()
    
    print("Acabó")

if __name__ == "__main__":
    main()