# Agente.py (MODIFICADO)

import os
import json
import re
import subprocess
import unicodedata
import requests
from difflib import get_close_matches
from typing import Optional, Dict
import vosk
import wave
from pydub import AudioSegment # Necesitarás: pip install pydub


# --- INICIO DE LA CORRECCIÓN ---
# Esta línea encuentra la carpeta donde está Agente.py
APP_DIR = os.path.dirname(os.path.abspath(__file__)) 

# Esta línea busca "vosk-model-small-es-0.22" DENTRO de esa misma carpeta
RUTA_MODELO_VOSK = os.path.join(APP_DIR, "vosk-model-es-0.42")
# --- FIN DE LA CORRECCIÓN ---


# ====== CATÁLOGOS ======
# Importar desde tus catalogos.py. Asegúrate de que Flask pueda verlos.
try:
    from catalogos import estados, municipios, TipoCultivo
except Exception:
    print("ADVERTENCIA: No se pudieron cargar los catálogos en Agente.py")
    estados, municipios, TipoCultivo = [], [], []

MESES_MAP = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12
}

# --- Utilidades de normalización (ESTAS SE QUEDAN IGUAL) ---
def _norm(s: str) -> str:
    if not isinstance(s, str):
        return s
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.lower().strip()

ESTADOS_N = {_norm(x): x for x in estados}
MUNICIPIOS_N = {_norm(x): x for x in municipios}
CULTIVOS_N = {_norm(x): x for x in TipoCultivo}

def _match_best(token: str, pool: Dict[str, str], cutoff: float = 0.8) -> Optional[str]:
    if not token:
        return None
    cand = get_close_matches(_norm(token), list(pool.keys()), n=1, cutoff=cutoff)
    return pool[cand[0]] if cand else None

# --- TTS (se elimina gTTS) ---
# La función 'hablar' se moverá al JAVASCRIPT usando la API del navegador.

# --- Reconocimiento de voz (MODIFICADO) ---
# Se elimina 'escuchar()' y '_callback()'
# Se reemplaza con una función que transcribe un ARCHIVO de audio.

if not os.path.isdir(RUTA_MODELO_VOSK):
    print(f"⚠️ No se encontró el modelo Vosk en {RUTA_MODELO_VOSK}.")
modelo_voz = vosk.Model(RUTA_MODELO_VOSK)

# En SiembraMasWeb/Agente.py
# (Asegúrate de que 'import os', 'import json' y 'from pydub import AudioSegment' estén al inicio)

def transcribir_desde_archivo(ruta_archivo_audio: str) -> str:
    """
    Toma la ruta de un archivo de audio (webm),
    lo convierte a WAV 16kHz mono USANDO FFMPEG DIRECTAMENTE (saltando pydub),
    y lo transcribe con Vosk.
    """
    temp_wav = f"{ruta_archivo_audio}_temp.wav"
    
    try:
        # --- INICIO DE LA CONVERSIÓN CON SUBPROCESS (MÉTODO ROBUSTO) ---
        print(f"[FFMPEG] Intentando convertir {ruta_archivo_audio} a {temp_wav}")
        
        # Este es el comando que ejecutarías en la terminal:
        # ffmpeg -i entrada.webm -ar 16000 -ac 1 -c:a pcm_s16le salida.wav
        comando = [
            'ffmpeg',
            '-i', ruta_archivo_audio,  # Archivo de entrada
            '-ar', '16000',             # Tasa de muestreo (Audio Rate) a 16kHz
            '-ac', '1',                 # Canales de audio (Audio Channels) a 1 (Mono)
            '-c:a', 'pcm_s16le',        # Códec de audio: PCM estándar de 16 bits (perfecto para Vosk)
            '-y',                       # Sobrescribir el archivo de salida si existe
            temp_wav
        ]
        
        # Ejecutamos el comando
        subprocess.run(comando, check=True, capture_output=True, text=True)
        
        print(f"[FFMPEG] Conversión a WAV exitosa.")
        # --- FIN DE LA CONVERSIÓN CON SUBPROCESS ---

    except subprocess.CalledProcessError as e:
        print(f"[FFMPEG] ¡ERROR FATAL AL CONVERTIR!")
        print(f"[FFMPEG] Salida de error: {e.stderr}")
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        return ""
    except Exception as e:
        print(f"[PYTHON] Error inesperado al llamar a ffmpeg: {e}")
        return ""

    # --- LÓGICA DE VOSK (MÉTODO ROBUSTO CON LIBRERÍA 'wave') ---
    try:
        print("[VOSK] Abriendo archivo WAV...")
        wf = wave.open(temp_wav, "rb")

        # Verificamos que el WAV sea correcto
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print(f"[VOSK] ¡ERROR! El formato del WAV es incorrecto. Canales: {wf.getnchannels()}, Ancho: {wf.getsampwidth()}")
            wf.close()
            os.remove(temp_wav)
            return ""
        
        print("[VOSK] Formato WAV correcto (16kHz, Mono, PCM). Empezando transcripción...")
        
        reconocedor = vosk.KaldiRecognizer(modelo_voz, wf.getframerate())
        
        while True:
            datos = wf.readframes(4000) # Leemos frames
            if len(datos) == 0:
                break
            reconocedor.AcceptWaveform(datos)

        resultado = json.loads(reconocedor.FinalResult())
        texto_total = resultado.get("text", "").strip()
        
        print("[VOSK] Transcripción finalizada.")
        wf.close()

    except Exception as e:
        print(f"[VOSK] ¡ERROR FATAL AL TRANSCRIBIR! {e}")
        return ""
    # --- FIN VOSK ---

    # 3. Limpiar
    try:
        if os.path.exists(temp_wav):
            os.remove(temp_wav) 
    except Exception:
        pass
        
    print(f"🎤 Texto transcrito: {texto_total}")
    return texto_total.lower()
# --- Llamada a Gemma (ESTA SE QUEDA IGUAL) ---
def _call_gemma_ollama(prompt: str) -> str:
    """
    Llama al servidor de Ollama en la máquina host (anfitrión) 
    usando una petición HTTP.
    """
    
    ollama_url = "http://localhost:11434/api/generate"

    payload = {
        "model": "gemma:2b", # O el modelo que uses
        "prompt": prompt,
        "stream": False  # Queremos la respuesta completa
    }

    try:
        # Hacemos la petición POST al servidor Ollama del host
        response = requests.post(ollama_url, json=payload, timeout=120) # 30 segundos de espera
        response.raise_for_status() # Lanza un error si la respuesta es 4xx o 5xx
        
        data = response.json()
        
        # Extraemos solo el texto de la respuesta de Gemma
        return data.get("response", "").strip()

    except requests.exceptions.ConnectionError:
        print("\n--- ERROR DE CONEXIÓN CON OLLAMA ---")
        print(f"No se pudo conectar a: {ollama_url}")
        print("Asegúrate de que Ollama esté corriendo en tu máquina (host).")
        print("---------------------------------------\n")
        return "" # Devolvemos vacío para que el endpoint falle limpiamente
    except Exception as e:
        print(f"Error inesperado al llamar a Ollama: {e}")
        return ""

def interpretar_con_gemma(texto: str) -> Dict[str, Optional[str]]:
    """
    Gemma devuelve JSON con: ruta, lugar, cultivo, mes.
    Luego se hace post-proceso: mes -> número, y corrección de lugar/cultivo con catálogos.
    """
    system = (
        "Tu única tarea es analizar la ORDEN HABLADA y extraer parámetros. "
        "Responde SIEMPRE con un objeto JSON. NO respondas con texto conversacional, saludos o explicaciones. "
        "El JSON debe tener EXACTAMENTE estos campos: "
        'ruta ("Estados" | "Municipios" | null), lugar (string | null), '
        'cultivo (string | null), mes (1-12 | null). '
        "Si la ORDEN HABLADA no es clara, está vacía o no contiene información (ej. 'hola', 'pues', 'gracias'), "
        "responde OBLIGATORIAMENTE con todos los campos en null: "
        "{\"ruta\": null, \"lugar\": null, \"cultivo\": null, \"mes\": null}"
    )

    ejemplos = (
        "Ejemplos:\n"
        "\"Cómo estará la cosecha de frijol en Aguascalientes en septiembre\"\n"
        "{\"ruta\": \"Estados\", \"lugar\": \"Aguascalientes\", \"cultivo\": \"Frijol\", \"mes\": 9}\n\n"
        "\"Predice tomate en Xalapa en marzo, datos de municipios\"\n"
        "{\"ruta\": \"Municipios\", \"lugar\": \"Xalapa\", \"cultivo\": \"Tomate rojo (jitomate)\", \"mes\": 3}\n\n"
        "\"Quiero la siembra en Veracruz en noviembre\"\n"
        "{\"ruta\": \"Estados\", \"lugar\": \"Veracruz\", \"cultivo\": null, \"mes\": 11}\n"
    )

    user = f"Orden: {texto}\nResponde solo con el JSON."
    prompt = f"{system}\n\n{ejemplos}\n\n{user}"

    salida = _call_gemma_ollama(prompt)

    # Extraer JSON
    m = re.search(r"\{.*\}", salida, re.DOTALL)
    if not m:
        print("Error Gemma: No se encontró JSON en la salida.")
        return {"ruta": None, "lugar": None, "cultivo": None, "mes": None}
    try:
        raw = json.loads(m.group(0))
    except Exception as e:
        print(f"Error Gemma: JSON inválido. {e}")
        return {"ruta": None, "lugar": None, "cultivo": None, "mes": None}

    # --- INICIO DE LA LÓGICA CORREGIDA ---

    # 1. Normalizar mes (acepta string o número)
    mes_val_num = raw.get("mes")
    if isinstance(mes_val_num, str):
        mes_val_num = MESES_MAP.get(_norm(mes_val_num))
    elif isinstance(mes_val_num, (int, float)):
        mes_val_num = int(mes_val_num)
    else:
        mes_val_num = None

    # 2. Corrección de typos con catálogos
    lugar_raw = raw.get("lugar") or ""
    cultivo_raw = raw.get("cultivo") or ""

    lugar_ok = _match_best(lugar_raw, MUNICIPIOS_N, cutoff=0.82)
    ruta_ok = None
    if lugar_ok:
        ruta_ok = "Municipios"
    else:
        lugar_ok = _match_best(lugar_raw, ESTADOS_N, cutoff=0.8)
        if lugar_ok:
            ruta_ok = "Estados"

    # 3. Respetar ruta sugerida si vino bien formada
    ruta_raw = raw.get("ruta")
    if ruta_raw in ("Estados", "Municipios"):
        ruta_ok = ruta_raw if (ruta_raw or ruta_ok) else ruta_ok

    cultivo_ok = _match_best(cultivo_raw, CULTIVOS_N, cutoff=0.8) if cultivo_raw else None

    # 4. Convertir número de mes a Nombre (para el <select> del HTML)
    mes_nombre = None
    if isinstance(mes_val_num, int) and 1 <= mes_val_num <= 12:
         MESES_NUM_A_NOMBRE = {v: k.capitalize() for k, v in MESES_MAP.items() if k != "setiembre"}
         mes_nombre = MESES_NUM_A_NOMBRE.get(mes_val_num)

    # 5. Devolver el JSON final
    datos_finales = {
        "ruta": ruta_ok,
        "lugar": lugar_ok or (lugar_raw if lugar_raw else None),
        "cultivo": cultivo_ok or (cultivo_raw if cultivo_raw else None),
        "mes": mes_nombre, # Devolvemos "Enero", "Febrero", etc.
    }
    return datos_finales
    # --- FIN DE LA LÓGICA CORREGIDA ---


# --- Guardar parámetros (se elimina) ---
# Esto ya no es necesario, Flask devolverá el JSON al navegador.

# --- Bucle principal (se elimina) ---
# if __name__ == "__main__":
#     ... (todo esto se va) ...def transcribir_desde_archivo(ruta_archivo_audio: str) -> str:
    """
    Toma la ruta de un archivo de audio (ej. webm, ogg, mp3)
    lo convierte a WAV 16kHz mono y lo transcribe con Vosk.
    """
    temp_wav = f"{ruta_archivo_audio}_temp.wav"
    
    try:
        # --- INICIO DEPURACIÓN PYDUB ---
        print(f"[PYDUB] Intentando cargar archivo: {ruta_archivo_audio}")
        if not os.path.exists(ruta_archivo_audio):
            print(f"[PYDUB] ¡ERROR! El archivo de audio NO EXISTE en {ruta_archivo_audio}")
            return ""

        audio = AudioSegment.from_file(ruta_archivo_audio)
        
        print(f"[PYDUB] Audio cargado exitosamente.")
        print(f"[PYDUB] Duración del audio: {len(audio) / 1000.0} segundos.")
        print(f"[PYDUB] Canales: {audio.channels}")
        print(f"[PYDUB] Frame Rate: {audio.frame_rate}")

        if len(audio) == 0:
            print("[PYDUB] ¡ERROR! El audio está vacío (0 segundos).")
            return ""

        # 1. Convertir el audio a formato WAV 16kHz mono
        audio = audio.set_channels(1).set_frame_rate(16000)
        
        print("[PYDUB] Audio convertido a 16kHz Mono.")
        
        audio.export(temp_wav, format="wav")
        print(f"[PYDUB] Archivo WAV temporal exportado en: {temp_wav}")
        # --- FIN DEPURACIÓN PYDUB ---
        
        wf = open(temp_wav, "rb")

    except Exception as e:
        print(f"[PYDUB] ¡ERROR FATAL AL CONVERTIR! Pydub/FFmpeg falló: {e}")
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        return ""

    # --- Lógica de VOSK (esta ya la tienes) ---
    reconocedor = vosk.KaldiRecognizer(modelo_voz, 16000)
    
    print("[VOSK] Empezando transcripción...")
    while True:
        datos = wf.read(4000)
        if len(datos) == 0:
            break
        reconocedor.AcceptWaveform(datos) 

    resultado = json.loads(reconocedor.FinalResult())
    texto_total = resultado.get("text", "").strip()
    
    print("[VOSK] Transcripción finalizada.")
    # --- FIN VOSK ---

    # 3. Limpiar
    wf.close()
    try:
        # Si quieres guardar el WAV para escucharlo, comenta la línea de abajo
        if os.path.exists(temp_wav):
            os.remove(temp_wav) 
    except Exception:
        pass
        
    print(f"🎤 Texto transcrito: {texto_total}")
    return texto_total.lower()