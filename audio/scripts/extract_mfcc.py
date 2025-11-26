# scripts/extract_mfcc.py
import os
import sys
import librosa
import numpy as np
from tqdm import tqdm

# Importar configuración global
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.append(PROJECT_DIR)

from audio.config import (
    AUDIO_DIR,
    MFCC_DIR,
    SAMPLE_RATE,
    N_MFCC,
    FRAME_SIZE,
    HOP_LENGTH,
    RESULTS_DIR
)

# ============================================================
# NORMALIZACIÓN GLOBAL DEL TRACK_ID (SIEMPRE 6 DÍGITOS)
# ============================================================

def normalize_tid(tid: str | int) -> str:
    try:
        tid_int = int(str(tid).strip())
        return f"{tid_int:06d}"
    except:
        return str(tid).strip().zfill(6)

# ============================================================
# UTILIDADES DE PREPROCESAMIENTO
# ============================================================

def pre_emphasis(signal, coeff=0.97):
    return np.append(signal[0], signal[1:] - coeff * signal[:-1])

def normalize_audio(y):
    if np.max(np.abs(y)) < 1e-8:
        return y
    return y / np.max(np.abs(y))

# ============================================================
# EXTRACCIÓN DE MFCC
# ============================================================

def extract_mfcc_from_audio(file_path):
    try:
        audio, _ = librosa.load(file_path, sr=SAMPLE_RATE, mono=True)
        audio = normalize_audio(audio)
        audio = pre_emphasis(audio)

        if len(audio) < FRAME_SIZE:
            raise RuntimeError(f"Audio demasiado corto para análisis: {file_path}")

        mfcc = librosa.feature.mfcc(
            y=audio,
            sr=SAMPLE_RATE,
            n_mfcc=N_MFCC,
            n_fft=FRAME_SIZE,
            hop_length=HOP_LENGTH
        )
        return mfcc.T

    except Exception as e:
        raise RuntimeError(f"Error procesando {file_path}: {e}")

# ============================================================
# PROCESAR TODOS LOS AUDIOS
# ============================================================

def process_all_audios():
    os.makedirs(MFCC_DIR, exist_ok=True)

    log_path = os.path.join(RESULTS_DIR, "mfcc_errors.log")
    error_log = open(log_path, "w", encoding="utf-8")

    print(f"\n Buscando audios en: {AUDIO_DIR}")

    valid_ext = {".mp3", ".wav", ".flac", ".ogg"}
    audio_files = []

    for root, _, files in os.walk(AUDIO_DIR):
        for f in files:
            if os.path.splitext(f)[1].lower() in valid_ext:
                audio_files.append(os.path.join(root, f))

    print(f" Audios encontrados: {len(audio_files)}")
    print(" Extrayendo MFCC...\n")

    for file_path in tqdm(audio_files):

        file_name = os.path.basename(file_path)
        raw_tid = os.path.splitext(file_name)[0]
        track_id = normalize_tid(raw_tid)  # <-- FIX PRINCIPAL

        output_file = os.path.join(MFCC_DIR, f"{track_id}.npy")

        if os.path.exists(output_file):
            continue

        try:
            mfcc = extract_mfcc_from_audio(file_path)
            np.save(output_file, mfcc)

        except Exception as e:
            error_log.write(str(e) + "\n")

    error_log.close()

    print("\n Extracción de MFCC completa.")
    print(f"   Errores registrados en: {log_path}")

if __name__ == "__main__":
    process_all_audios()
