import psycopg2
import numpy as np
import os
import glob
import random
import time

 
CARPETA_DATOS = "./audio/features/histograms"
N_VALUES = [2000, 4000, 8000, 16000, 32000] 

DB_CONFIG = {
    "host": "localhost", "port": "5433", 
    "user": "dianananez", "password": "proyecto2bd", "dbname": "multimedia_db"
}


def conectar():
    return psycopg2.connect(**DB_CONFIG)

def main():
    print("=" * 60)

    print(f"Leyendo archivos desde: {CARPETA_DATOS}")
    archivos = glob.glob(os.path.join(CARPETA_DATOS, "*.npy"))
    
    if not archivos:
        print("ERROR: No encontré archivos .npy")
        return
    
    # Leer un archivo para detectar dimensión
    ejemplo = np.load(archivos[0])
    if ejemplo.ndim == 1:
        vector_ejemplo = ejemplo.tolist()
    else:
        vector_ejemplo = np.mean(ejemplo.T, axis=0).tolist()
        
    DIMENSION = len(vector_ejemplo)
    print(f"Dimensión detectada: {DIMENSION}")

    # Cargar vectores en una lista gigante en memoria
    vectores_memoria = []
    print("Cargando archivos...")
    
    # Leemos todos los archivos
    for ruta in archivos: 
        try:
            d = np.load(ruta)
            v = d.tolist() if d.ndim == 1 else np.mean(d.T, axis=0).tolist()
            if len(v) == DIMENSION:
                vectores_memoria.append(v)
        except: pass

    print(f"Vectores reales cargados: {len(vectores_memoria)}")

    MAX_N = max(N_VALUES)
    while len(vectores_memoria) < MAX_N:
        print(f"Tienes {len(vectores_memoria)}, pero necesitamos {MAX_N}. Duplicando datos...")
        vectores_memoria += vectores_memoria
    
#recorte de memoria
        vectores_memoria = vectores_memoria[:MAX_N] 
    
    print(f"Total listo para el experimento: {len(vectores_memoria)}")
    print("-" * 60)
    print(f"{'N (Cantidad)':<15} | {'Tiempo Búsqueda (s)':<20} | {'Estado'}")
    print("-" * 60)

    conn = conectar()
    conn.autocommit = True
    cur = conn.cursor()

    for n in N_VALUES:
        cur.execute("DROP TABLE IF EXISTS experimento_audio;")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(f"CREATE TABLE experimento_audio (id SERIAL PRIMARY KEY, embedding vector({DIMENSION}));")
        
        lote = vectores_memoria[:n]
        datos_sql = [(v,) for v in lote]
        
        for i in range(0, len(datos_sql), 1000):
            chunk = datos_sql[i:i+1000]
            args = ','.join(cur.mogrify("(%s)", x).decode('utf-8') for x in chunk)
            cur.execute("INSERT INTO experimento_audio (embedding) VALUES " + args)
        
        try:
            cur.execute("CREATE INDEX ON experimento_audio USING hnsw (embedding vector_l2_ops);")
        except: pass 

        query = str(np.random.rand(DIMENSION).tolist()) # Vector random para buscar
        tiempos = []
        for _ in range(5): # Hacemos 5 intentos para sacar promedio
            t0 = time.time()
            cur.execute(f"SELECT id FROM experimento_audio ORDER BY embedding <-> '{query}' LIMIT 8;")
            cur.fetchall()
            tiempos.append(time.time() - t0)
        
        promedio = sum(tiempos) / len(tiempos)
        print(f"{n:<15} | {promedio:.6f}             | Listo")

    cur.close()
    conn.close()
    print("Acabó")

if __name__ == "__main__":
    main()