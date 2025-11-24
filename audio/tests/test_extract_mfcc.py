# proyecto_2/tests/test_extract_mfcc.py

import os
import random
import numpy as np

from config import AUDIO_DIR, MFCC_DIR
from scripts.extract_mfcc import process_all_audios


def main():
    print("=== TEST: EXTRACCIÓN DE MFCC ===")
    print(f"AUDIO_DIR: {AUDIO_DIR}")
    print(f"MFCC_DIR:  {MFCC_DIR}")
    print()

    # 1) Verificar que la carpeta de audios existe
    if not os.path.isdir(AUDIO_DIR):
        raise FileNotFoundError(
            f"No se encontró AUDIO_DIR: {AUDIO_DIR}\n"
            "Verifica la ruta en config.py"
        )

    # 2) Crear la carpeta de salida si no existe
    os.makedirs(MFCC_DIR, exist_ok=True)

    # 3) Ejecutar la extracción sobre todos los audios disponibles
    #    (si luego quieres limitar, habría que modificar process_all_audios).
    print("Extrayendo MFCC para los audios de prueba...")
    process_all_audios()

    # 4) Revisar qué archivos .npy se generaron
    mfcc_files = [f for f in os.listdir(MFCC_DIR) if f.endswith(".npy")]
    print(f"\nArchivos MFCC generados en {MFCC_DIR}:")
    for f in mfcc_files:
        print("  -", f)

    if not mfcc_files:
        raise RuntimeError(
            "No se generó ningún archivo .npy en MFCC_DIR.\n"
            "Revisa que process_all_audios esté guardando MFCC correctamente."
        )

    # 5) Cargar uno al azar y revisar su forma (frames x coeficientes)
    sample_file = random.choice(mfcc_files)
    sample_path = os.path.join(MFCC_DIR, sample_file)
    mfcc = np.load(sample_path)

    print(f"\nEjemplo de archivo MFCC: {sample_file}")
    print("Forma del array (frames, n_mfcc):", mfcc.shape)
    print("Tipo de datos:", mfcc.dtype)
    print("\n TEST MFCC COMPLETADO SIN ERRORES.")


if __name__ == "__main__":
    main()
