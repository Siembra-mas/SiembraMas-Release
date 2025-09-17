# app.py (versión corregida y robusta)
from flask import Flask, render_template, request, jsonify, abort
import unicodedata
import re
import pandas as pd
from datetime import datetime
from functools import lru_cache
from typing import Dict, Tuple, Optional

# ======================== Dependencias del proyecto ==========================
from prediccion import Prediccion
from cultivos import obtener_cultivos
from catalogos import estados, municipios, Lugar, coordenadas, coordenadas_municipios

# =============================== Config Flask ================================
app = Flask(__name__, template_folder="templates", static_folder="static")

# ================================= Utilidades ================================
def normalizar_texto(texto: str) -> str:
    """Quita acentos y pasa a MAYÚSCULAS (para comparaciones robustas)."""
    if not isinstance(texto, str):
        return texto
    texto = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode("utf-8")
    return texto.upper()

def slug_cultivo(nombre: str) -> str:
    """Crea un slug de archivo/imagen a partir del nombre del cultivo."""
    s = unicodedata.normalize("NFD", nombre).encode("ascii", "ignore").decode("utf-8")
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s

def nearest_by_coords(lat: float, lon: float, pool_dict: Dict[str, Tuple[float, float]]) -> Optional[str]:
    """Devuelve la clave del diccionario con coordenadas más cercana a (lat, lon)."""
    mejor_clave, mejor_d = None, float("inf")
    for clave, coords in pool_dict.items():
        try:
            la, lo = float(coords[0]), float(coords[1])
        except Exception:
            continue  # ignora coordenadas inválidas
        d = (la - lat) ** 2 + (lo - lon) ** 2
        if d < mejor_d:
            mejor_clave, mejor_d = clave, d
    return mejor_clave

def buscar_coords(ruta: str, lugar: str):
    """
    Devuelve (lat, lon) usando los catálogos de coordenadas según la ruta.
    - Estados  -> usa `coordenadas`
    - Municipios -> usa `coordenadas_municipios`
    Compara con claves normalizadas para evitar problemas de acentos/mayúsculas.
    """
    if not lugar:
        return None, None
    
    pool = coordenadas_municipios if ruta == "Municipios" else coordenadas

    # mapa normalizado -> (lat, lon)
    pool_norm = {normalizar_texto(k): v for k, v in pool.items()}
    return pool_norm.get(normalizar_texto(lugar), (None, None))

def calcular_probabilidad(temp_min_pred: float, temp_max_pred: float, tmin_ok: float, tmax_ok: float) -> float:
    """
    Calcula un % de cercanía al rango [tmin_ok, tmax_ok] (0-100).
    Considera la distancia de los extremos respecto al rango óptimo.
    """
    if tmax_ok == tmin_ok:
        return 0.0
    dentro_min = max(0, min(1, (temp_max_pred - tmin_ok) / (tmax_ok - tmin_ok)))
    dentro_max = max(0, min(1, (tmax_ok - temp_min_pred) / (tmax_ok - tmin_ok)))
    return round(((dentro_min + dentro_max) / 2) * 100, 1)

# ================================= Constantes ================================
MESES = (
    "Enero","Febrero","Marzo","Abril","Mayo","Junio",
    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"
)
ANIOS = (datetime.now().year,)  # año actual por defecto

def mes_actual_nombre() -> str:
    """Devuelve el nombre del mes actual en español, usando MESES."""
    idx = datetime.now().month  # 1..12
    return MESES[idx - 1]

# ======================= Cargas únicas / Cache en memoria ====================
# Carga única del CSV de condiciones (si no existe, usa DF vacío sin romper)
try:
    CONDICIONES_DF = pd.read_csv("./CondicionesIdeales/CondicionesIdeales.csv", encoding="utf-8")
    CONDICIONES_DF["Cultivo_normalizado"] = CONDICIONES_DF["Cultivo"].apply(normalizar_texto)
except Exception:
    CONDICIONES_DF = pd.DataFrame(columns=["Cultivo", "Temp min optima", "Temp max optima", "Cultivo_normalizado"])

@lru_cache(maxsize=512)
def _pred_cache(ruta: str, lugar: str, mes_solicitado: int, cultivo: Optional[str]):
    """
    Cachea llamadas a Prediccion(...) por parámetros.
    - mes_solicitado: 1..12
    - cultivo: None para clima general; str para cultivo específico
    """
    return Prediccion(ruta=ruta, lugar=lugar, mes_solicitado=mes_solicitado, Cultivo=cultivo)

# ================================== Rutas ====================================
@app.route("/", methods=["GET"])
def home():
    """Página de inicio: preselecciona el mes actual y muestra selects base."""
    context = dict(
        ruta_opciones=Lugar,
        estados=estados,
        municipios=municipios,
        meses=MESES,                 
        anios=ANIOS,
        ruta_sel="Estados",
        estado_sel="",
        municipio_sel="",
        mes_sel=mes_actual_nombre(),   # mes actual por defecto
        anio_sel=ANIOS[0],
        temp_max=None,
        temp_min=None,
        temp_media=None,
        precipitacion=None,
        humedad=None,
        nombre_mes=None,
        recomendaciones=[],
        coordenadas=coordenadas,
        coordenadas_municipios=coordenadas_municipios,
    )
    return render_template("inicio_sm.html", **context)

@app.route("/ubicarme", methods=["POST"])
def ubicarme():
    """
    Dado (lat, lon), devuelve Estado o Municipio más cercano.
    Valida parámetros y responde JSON claro o 400 en caso de error.
    """
    data = request.get_json(silent=True) or {}
    try:
        lat = float(data.get("lat", ""))
        lon = float(data.get("lon", ""))
    except Exception:
        abort(400, description="Parámetros 'lat' y 'lon' inválidos o ausentes.")

    municipio_cercano = nearest_by_coords(lat, lon, coordenadas_municipios)
    if municipio_cercano:
        return jsonify({"ruta": "Municipios", "lugar": municipio_cercano})

    estado_cercano = nearest_by_coords(lat, lon, coordenadas)
    if estado_cercano:
        return jsonify({"ruta": "Estados", "lugar": estado_cercano})

    abort(404, description="No se encontró una ubicación cercana válida.")

@app.route("/generar", methods=["POST"])
def generar():
    """
    Arma el contexto con predicciones (clima general) y recomendaciones por cultivo.
    Reglas:
      - Si falta 'lugar' (estado/municipio), renderiza sin cálculos.
      - 'mes' por defecto es el mes actual; se pasa 1..12 a Prediccion.
    """
    ruta = (request.form.get("ruta") or "Estados").strip()
    estado = (request.form.get("estado") or "").strip()
    municipio = (request.form.get("municipio") or "").strip()

    mes_texto = (request.form.get("mes") or mes_actual_nombre()).strip()
    anio = int(request.form.get("anio") or ANIOS[0])

    # Índice de mes para el modelo (1..12)
    try:
        mes_solicitado = MESES.index(mes_texto) + 1
    except ValueError:
        # Si viene un mes inválido, usa el actual
        mes_texto = mes_actual_nombre()
        mes_solicitado = MESES.index(mes_texto) + 1

    # Determina el 'lugar' y el CSV de cultivos según la ruta
    if ruta == "Estados":
        lugar = estado
        ruta_csv_cultivos = "./Ideal/CultivoEstado.csv"
    else:
        ruta = "Municipios"  # normaliza valor
        lugar = municipio
        ruta_csv_cultivos = "./Ideal/CultivoMunicipio.csv"

    # Si no hay lugar, regresa vista básica con el mes/año ya establecidos
    if not lugar:
        context = dict(
            ruta_opciones=Lugar,
            estados=estados,
            municipios=municipios,
            meses=MESES,
            anios=ANIOS,
            ruta_sel=ruta,
            estado_sel=estado,
            municipio_sel=municipio,
            mes_sel=mes_texto,
            anio_sel=anio,
            temp_max=None,
            temp_min=None,
            temp_media=None,
            precipitacion=None,
            humedad=None,
            nombre_mes=None,
            recomendaciones=[],
            coordenadas=coordenadas,
            coordenadas_municipios=coordenadas_municipios,
        )
        return render_template("inicio_sm.html", **context)

    # ======================= Predicción clima general ========================
    temp_min = temp_max = temp_media = None
    try:
        df_pred = _pred_cache(ruta, lugar, mes_solicitado, None)
        if isinstance(df_pred, pd.DataFrame) and not df_pred.empty:
            r0 = df_pred.iloc[0]
            # Redondeo a enteros
            temp_min = int(round(float(r0["Pred_TempMin"])))
            temp_max = int(round(float(r0["Pred_tempMax"])))
            temp_media = int(round((temp_min + temp_max) / 2.0))
    except Exception:
        # En caso de error del modelo, deja métricas como None
        pass

    nombre_mes = mes_texto
    precipitacion = None
    humedad = None

    # ========================= Recomendaciones por cultivo ===================
    recomendaciones = []
    try:
        dic_cultivos = obtener_cultivos(ruta_csv_cultivos)
    except Exception:
        dic_cultivos = {}

    dic_norm = {normalizar_texto(k): v for k, v in dic_cultivos.items()}
    lista_cultivos = dic_norm.get(normalizar_texto(lugar), []) if lugar else []

    for cultivo in lista_cultivos:
        try:
            df_c = _pred_cache(ruta, lugar, mes_solicitado, cultivo)
            if not isinstance(df_c, pd.DataFrame) or df_c.empty:
                continue

            r0 = df_c.iloc[0]
            tmin_pred = int(round(float(r0["Pred_TempMin"])))
            tmax_pred = int(round(float(r0["Pred_tempMax"])))

            # Busca condiciones óptimas (si existen)
            texto = ""
            prob = None
            if not CONDICIONES_DF.empty:
                c_norm = normalizar_texto(cultivo)
                cond = CONDICIONES_DF[CONDICIONES_DF["Cultivo_normalizado"] == c_norm]
                if not cond.empty:
                    tmin_ok = float(cond["Temp min optima"].iloc[0])
                    tmax_ok = float(cond["Temp max optima"].iloc[0])
                    prob = calcular_probabilidad(tmin_pred, tmax_pred, tmin_ok, tmax_ok)

                    if prob >= 70:
                        texto = f"✅ Alta probabilidad ({prob}%) de siembra de {cultivo}"
                    elif prob >= 40:
                        texto = f"⚠️ Posible siembra ({prob}%) de {cultivo}"
                    else:
                        texto = f"❌ No conviene ({prob}%) de siembra de {cultivo}"
                else:
                    texto = f"No hay condiciones registradas para {cultivo}"
            else:
                texto = f"No hay tabla de condiciones cargada. Revisa CondicionesIdeales.csv"

            recomendaciones.append({
                "cultivo": cultivo,
                "prob": prob,
                "texto": texto,
                "img_slug": slug_cultivo(cultivo)
            })
        except Exception:
            # Si algo falla para un cultivo, lo omitimos y seguimos con el resto
            continue

    # ================================ Contexto ===============================
    context = dict(
        ruta_opciones=Lugar,
        estados=estados,
        municipios=municipios,
        meses=MESES,
        anios=ANIOS,
        ruta_sel=ruta,
        estado_sel=estado,
        municipio_sel=municipio,
        mes_sel=mes_texto,
        anio_sel=anio,
        temp_max=temp_max,
        temp_min=temp_min,
        temp_media=temp_media,
        precipitacion=precipitacion,
        humedad=humedad,
        nombre_mes=nombre_mes,
        recomendaciones=recomendaciones,
        coordenadas=coordenadas,
        coordenadas_municipios=coordenadas_municipios,
    )
    return render_template("inicio_sm.html", **context)

# ================================== Main =====================================
if __name__ == "__main__":
    app.run(debug=True)
