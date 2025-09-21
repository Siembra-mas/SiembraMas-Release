# app_inicio.py
# === Rutas y utilidades para la página INICIO (inicio_sm.html) ===
# ***NOTA***: Este archivo replica la lógica original de "inicio" que estaba en app.py,
# sin modificar el contenido de las funciones (solo se cambiaron decoradores @app.* por @bp.*).
from flask import Blueprint, render_template, request, jsonify
import unicodedata
import re
import pandas as pd
from datetime import datetime
from functools import lru_cache
from typing import Dict, Tuple, Optional
import requests
from calendar import monthrange

# ======================== Dependencias del proyecto ==========================
from prediccion import Prediccion
from cultivos import obtener_cultivos
from catalogos import estados, municipios, Lugar, coordenadas, coordenadas_municipios

# ============================ Blueprint Inicio ===============================
bp = Blueprint("inicio", __name__, url_prefix="")

# ================================= Utilidades ================================
def normalizar_texto(texto: str) -> str:
    """Quita acentos y pasa a MAYÚSCULAS (para comparaciones robustas)."""
    if not isinstance(texto, str):
        return texto
    # Corrección para manejar comas en números decimales
    if isinstance(texto, str) and ',' in texto:
        texto = texto.replace(',', '.')
    texto = unicodedata.normalize("NFD", str(texto)).encode("ascii", "ignore").decode("utf-8")
    return texto.upper()

def slug_cultivo(nombre: str) -> str:
    """Crea un slug de archivo/imagen a partir del nombre del cultivo."""
    s = unicodedata.normalize("NFD", nombre).encode("ascii", "ignore").decode("utf-8")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s

def buscar_coords(ruta: str, lugar: str) -> Tuple[Optional[float], Optional[float]]:
    """Devuelve (lat, lon) usando los catálogos de coordenadas."""
    if not lugar: return None, None
    pool = coordenadas_municipios if ruta == "Municipios" else coordenadas
    pool_norm = {normalizar_texto(k): v for k, v in pool.items()}
    return pool_norm.get(normalizar_texto(lugar), (None, None))

def obtener_clima_api(lat: float, lon: float, mes: int, anio: int) -> Tuple[Optional[float], Optional[float]]:
    """Obtiene la predicción de precipitación y humedad de la API de Open-Meteo."""
    if not all([lat, lon, mes, anio]): return None, None
    _, num_dias = monthrange(anio, mes)
    start_date, end_date = f"{anio}-{mes:02d}-01", f"{anio}-{mes:02d}-{num_dias}"
    api_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&daily=precipitation_sum,relative_humidity_2m_mean&timezone=auto"
        f"&start_date={start_date}&end_date={end_date}"
    )
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json().get("daily", {})
        precipitacion_total = sum(data.get("precipitation_sum", [0]))
        humedad_promedio = sum(data.get("relative_humidity_2m_mean", [1])) / len(data.get("relative_humidity_2m_mean", [1]))
        return round(precipitacion_total, 1), round(humedad_promedio, 1)
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Falló la llamada a la API del clima. Causa: {e}")
        return None, None

def calcular_probabilidad_avanzada(preds: dict, optimos: dict, pesos=None, config=None):
    # Pesos incluyen tmed; si no quieres usarlo, pon tmed: 0.0
    if pesos is None:
        pesos = {"tmin": 0.18, "tmax": 0.18, "tmed": 0.24, "precip": 0.24, "hum": 0.16}
    if config is None:
        config = {
            "precip_deficit_tol": 0.20,  # 20% por debajo del óptimo => 0
            "hum_tolerancia": 0.10,      # ±10% sin penalizar
            "hum_rolloff": 0.50,         # caída suave fuera de la banda
            "temp_holgura_c": 5.0,       # holgura (°C) fuera del rango (tmin/tmax)
            "tmed_holgura_c": 3.0,       # holgura (°C) alrededor de la tmedia óptima
        }

    def clamp01(x):
        return 0.0 if x <= 0 else (1.0 if x >= 1 else x)

    def score_precipitacion(pred, p_opt, deficit_tol):
        if p_opt <= 0: return 0.0
        if pred >= p_opt: return 1.0  # más lluvia que el óptimo no penaliza
        piso = p_opt * (1.0 - deficit_tol)
        if pred <= piso: return 0.0
        return (pred - piso) / (p_opt - piso)

    def score_humedad(pred, h_opt, tol_centro, rolloff):
        if h_opt <= 0: return 0.0
        delta_rel = abs(pred - h_opt) / h_opt
        if delta_rel <= tol_centro: return 1.0
        exceso = delta_rel - tol_centro
        if exceso >= rolloff: return 0.0
        return 1.0 - (exceso / rolloff)

    def score_temperatura(valor, rango_min, rango_max, holgura):
        # Lineal hacia 0 fuera del rango permitido con holgura
        if rango_min is None or rango_max is None: return 0.0
        if rango_min > rango_max: rango_min, rango_max = rango_max, rango_min
        if rango_min <= valor <= rango_max: return 1.0
        distancia = (rango_min - valor) if valor < rango_min else (valor - rango_max)
        if distancia >= holgura: return 0.0
        return 1.0 - (distancia / holgura)

    def score_temperatura_central(valor, t_opt, holgura):
        # Máximo en t_opt; cae linealmente hasta 0 en ±holgura
        if t_opt is None or holgura is None or holgura <= 0: return 0.0
        d = abs(valor - t_opt)
        if d >= holgura: return 0.0
        return 1.0 - (d / holgura)

    # Óptimos centrales (si no vienen explícitos)
    p_opt = optimos.get("p_opt", (optimos["pmin"] + optimos["pmax"]) / 2.0)
    h_opt = optimos.get("h_opt", (optimos["hmin"] + optimos["hmax"]) / 2.0)

    # Temperaturas pronosticadas
    tmin_pred = preds.get("tmin")
    tmax_pred = preds.get("tmax")
    tmed_pred = preds.get("tmed", None)
    if tmed_pred is None and (tmin_pred is not None and tmax_pred is not None):
        tmed_pred = (tmin_pred + tmax_pred) / 2.0  # fallback automático

    # Óptimos para temperatura media
    tmed_opt = optimos.get("tmed_opt", None)
    if tmed_opt is None and ("tmin" in optimos and "tmax" in optimos):
        tmed_opt = (optimos["tmin"] + optimos["tmax"]) / 2.0

    # Scores
    s_tmin = score_temperatura(tmin_pred, optimos["tmin"], optimos["tmax"], config["temp_holgura_c"])
    s_tmax = score_temperatura(tmax_pred, optimos["tmin"], optimos["tmax"], config["temp_holgura_c"])
    s_tmed = score_temperatura_central(tmed_pred, tmed_opt, config["tmed_holgura_c"]) if tmed_pred is not None else 0.0
    s_prec = score_precipitacion(preds["precip"], p_opt, config["precip_deficit_tol"])
    s_hum  = score_humedad(preds["hum"], h_opt, config["hum_tolerancia"], config["hum_rolloff"])

    # Combinación ponderada (auto-normaliza por suma de pesos)
    total_pesos = sum(pesos.values()) or 1.0
    score = (
        pesos.get("tmin", 0.0)   * s_tmin +
        pesos.get("tmax", 0.0)   * s_tmax +
        pesos.get("tmed", 0.0)   * s_tmed +
        pesos.get("precip", 0.0) * s_prec +
        pesos.get("hum", 0.0)    * s_hum
    ) / total_pesos

    valor = int(round(100 * clamp01(score)))
    return 99 if valor == 100 else valor

# ================================= Constantes y Carga de Datos ================================
MESES = ("Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre")
ANIOS = (datetime.now().year,)
def mes_actual_nombre() -> str: return MESES[datetime.now().month - 1]

try:
    CONDICIONES_DF = pd.read_csv("./CondicionesIdeales/CondicionesIdeales.csv", encoding="utf-8")
    CONDICIONES_DF.columns = [col.strip().replace(' ', '_') for col in CONDICIONES_DF.columns]
    CONDICIONES_DF["Cultivo_normalizado"] = CONDICIONES_DF["Cultivo"].apply(normalizar_texto)
    print("INFO: 'CondicionesIdeales.csv' cargado y procesado.")
except Exception as e:
    print(f"ERROR CRÍTICO: No se pudo cargar 'CondicionesIdeales.csv'. Causa: {e}")
    CONDICIONES_DF = pd.DataFrame()

@lru_cache(maxsize=128)
def _pred_cache(ruta: str, lugar: str, mes_solicitado: int):
    return Prediccion(ruta=ruta, lugar=lugar, mes_solicitado=mes_solicitado)

# ================================== Rutas (solo decoradores cambiados) =======================
@bp.route("/", methods=["GET"])
def home():
    """Página de inicio que muestra el formulario base."""
    context = {
        "mes_sel": mes_actual_nombre(), "anio_sel": ANIOS[0], "recomendaciones": [],
        "estados": estados, "municipios": municipios, "meses": MESES, "anios": ANIOS,
        "coordenadas": coordenadas, "coordenadas_municipios": coordenadas_municipios
    }
    return render_template("inicio_sm.html", **context)

@bp.route("/generar", methods=["POST"])
def generar():
    """Genera y muestra la lista de cultivos recomendados usando el recomendador avanzado."""
    # --- 1. Recolección y validación de datos del formulario ---
    ruta = request.form.get("ruta", "Estados")
    lugar = request.form.get("estado") if ruta == "Estados" else request.form.get("municipio")
    mes_texto = request.form.get("mes", mes_actual_nombre())
    anio = int(request.form.get("anio", ANIOS[0]))
    mes_solicitado = MESES.index(mes_texto) + 1

    print(f"\n--- Solicitud de recomendación ---")
    if not lugar: print("ADVERTENCIA: No se seleccionó un lugar. Abortando cálculo.")
    else: print(f"INFO: Procesando para '{lugar}' en {mes_texto} de {anio}.")

    # --- 2. Obtención de datos climáticos (Modelo local + API externa) ---
    temp_min, temp_max, precipitacion, humedad = None, None, None, None
    if lugar:
        try:
            df_pred = _pred_cache(ruta, lugar, mes_solicitado)
            temp_min, temp_max = int(df_pred["Pred_TempMin"].iloc[0]), int(df_pred["Pred_tempMax"].iloc[0])
            print(f"INFO: Predicción de temperatura: {temp_min}°C - {temp_max}°C")
            
            lat, lon = buscar_coords(ruta, lugar)
            precipitacion, humedad = obtener_clima_api(lat, lon, mes_solicitado, anio)
            if precipitacion is not None:
                print(f"INFO: Datos de API: Precipitación={precipitacion}mm, Humedad={humedad}%")
        except Exception as e:
            print(f"ERROR: Faltan datos climáticos para '{lugar}'. Causa: {e}")

    # --- 3. Generación de recomendaciones avanzadas ---
    recomendaciones = []
    if lugar and all(v is not None for v in [temp_min, temp_max, precipitacion, humedad]):
        try:
            ruta_csv_cultivos = "./Ideal/CultivoEstado.csv" if ruta == "Estados" else "./Ideal/CultivoMunicipio.csv"
            lista_cultivos = obtener_cultivos(ruta_csv_cultivos).get(lugar, [])
            print(f"INFO: Se encontraron {len(lista_cultivos)} cultivos para '{lugar}'.")

            for cultivo in lista_cultivos:
                cond = CONDICIONES_DF[CONDICIONES_DF["Cultivo_normalizado"] == normalizar_texto(cultivo)]
                if not cond.empty:
                    # Crear rangos de tolerancia para precipitación y humedad
                    lluvia_opt  = float(str(cond["Lluvias_optima"].iloc[0]).replace(',', '.'))
                    humedad_opt = float(str(cond["Humedad"].iloc[0]).replace(',', '.'))
                    
                    optimos = {
                        "tmin": float(str(cond["Temp_min_optima"].iloc[0]).replace(',', '.')),
                        "tmax": float(str(cond["Temp_max_optima"].iloc[0]).replace(',', '.')),
                        "pmin": lluvia_opt * 0.8,  "pmax": lluvia_opt * 1.2,
                        "hmin": humedad_opt * 0.9, "hmax": humedad_opt * 1.1,
                        "p_opt": lluvia_opt,
                        "h_opt": humedad_opt,
                    }
                    preds = {"tmin": temp_min, "tmax": temp_max, "precip": precipitacion, "hum": humedad}

                    prob = calcular_probabilidad_avanzada(preds, optimos)
                    
                    if prob >= 70: texto = f"✅ Alta probabilidad ({prob}%) de éxito para la siembra."
                    elif prob >= 40: texto = f"⚠️ Probabilidad media ({prob}%). La siembra es posible con precauciones."
                    else: texto = f"❌ Baja probabilidad ({prob}%). No se recomienda la siembra este mes."
                    
                    recomendaciones.append({"cultivo": cultivo, "prob": prob, "texto": texto, "img_slug": slug_cultivo(cultivo)})
        except Exception as e:
            print(f"ERROR CRÍTICO: Fallo al procesar las recomendaciones. Causa: {e}")
            
    # --- 4. Renderizado final ---
    context = {
        "ruta_sel": ruta, "estado_sel": request.form.get("estado"), "municipio_sel": request.form.get("municipio"),
        "mes_sel": mes_texto, "anio_sel": anio, "recomendaciones": sorted(recomendaciones, key=lambda x: x['prob'], reverse=True),
        "temp_max": temp_max, "temp_min": temp_min, "temp_media": int((temp_min + temp_max) / 2) if temp_min is not None else None,
        "precipitacion": precipitacion, "humedad": humedad, "nombre_mes": mes_texto if lugar else None,
        "estados": estados, "municipios": municipios, "meses": MESES, "anios": ANIOS,
        "coordenadas": coordenadas, "coordenadas_municipios": coordenadas_municipios
    }
    return render_template("inicio_sm.html", **context)
