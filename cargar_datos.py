import psycopg2
import numpy as np
import os
import glob

# CONFIGURACIÓN 

CARPETA_DATOS = "./audio/features/histograms" 

def conectar_db():
    return psycopg2.connect(
        host="localhost",
        port="5433",
        user="dianananez",
        password="proyecto2bd",
        dbname="multimedia_db"
    )

def main():
    print("Conectando a la base de datos...")
    try:
        conn = conectar_db()
        cur = conn.cursor()
    except Exception as e:
        print(f"Error conectando: {e}")
        return

    # 1. Buscar archivos
    archivos = glob.glob(os.path.join(CARPETA_DATOS, "*.npy"))
    if not archivos:
        print(f"No encontré archivos en {CARPETA_DATOS}")
        return
    
    # Agregamos todos los archivos para la prueba
    archivos_prueba = archivos 

    # 2. Determinar dimensión
    # Cargamos el archivo
    datos = np.load(archivos_prueba[0])
    
    # SI ya es plano (1 dimensión), lo usamos tal cual. 
    # SI es matriz (2 dimensiones), sacamos el promedio.
    if datos.ndim == 1:
        vector_final = datos.tolist()
    else:
        vector_final = np.mean(datos.T, axis=0).tolist()

    DIMENSION = len(vector_final)
    print(f"Dimensión detectada: {DIMENSION}")

    # 3. Reiniciar Base de Datos
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute("DROP TABLE IF EXISTS audios_finales;")
    cur.execute(f"CREATE TABLE audios_finales (id bigserial PRIMARY KEY, nombre TEXT, embedding vector({DIMENSION}));")
    conn.commit()
    print("Tabla creada.")

    # 4. Insertar
    print("Cargando datos...")
    count_ok = 0
    
    for archivo in archivos_prueba:
        try:
            datos = np.load(archivo)
            
            # Misma lógica de arriba para cada archivo
            if datos.ndim == 1:
                vector = datos.tolist()
            else:
                vector = np.mean(datos.T, axis=0).tolist()

            # Validar dimensión
            if len(vector) != DIMENSION:
                print(f"Saltando {os.path.basename(archivo)}: Tamaño incorrecto")
                continue 

            nombre = os.path.basename(archivo)
            cur.execute("INSERT INTO audios_finales (nombre, embedding) VALUES (%s, %s)", (nombre, vector))
            conn.commit()
            count_ok += 1
            
        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")

    cur.close()
    conn.close()
    
    print("\n" + "="*30)
    print(f"Se guardaron {count_ok} audios.")
    print("="*30)

if __name__ == "__main__":
    main()