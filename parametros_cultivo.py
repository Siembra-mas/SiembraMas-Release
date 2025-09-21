
# -*- coding: utf-8 -*-
"""
parametros_cultivo.py
---------------------
Carga parámetros por cultivo desde un CSV (CondicionesIdeales.csv) y expone utilidades
para preparar `optimos`, `pesos` y `config` para la función `calcular_probabilidad_avanzada`.

Uso básico:
-----------
from parametros_cultivo import obtener_parametros

optimos, pesos, config = obtener_parametros("Arroz", fase="siembra")
score = calcular_probabilidad_avanzada(preds, optimos, pesos, config)
"""

from __future__ import annotations
from pathlib import Path
import csv
import unicodedata
from functools import lru_cache
from typing import Dict, Tuple, Optional

# Ruta por defecto del CSV (ajústala si usas otra)
CSV_PATH = Path("CondicionesIdeales.csv")  # se asume junto al proyecto/ejecución

# ---------------------
# Utilidades de texto
# ---------------------
def _normalizar_texto(s: str) -> str:
    """Minúsculas, sin acentos, sin espacios dobles."""
    if s is None:
        return ""
    s = s.strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = " ".join(s.split())
    return s

# ---------------------
# Carga de CSV robusta
# ---------------------
# Aliases de columnas permitidas -> llave estandar
HEADER_MAP = {
    # cultivo
    "cultivo": "cultivo",
    "crop": "cultivo",
    "nombre": "cultivo",
    "nombre_cultivo": "cultivo",

    # temperatura mínima óptima del rango
    "tmin": "tmin",
    "temp_min": "tmin",
    "temperatura_min": "tmin",
    "t_min": "tmin",

    # temperatura máxima óptima del rango
    "tmax": "tmax",
    "temp_max": "tmax",
    "temperatura_max": "tmax",
    "t_max": "tmax",

    # precipitación (rango)
    "pmin": "pmin",
    "precip_min": "pmin",
    "precipitacion_min": "pmin",
    "lluvia_min": "pmin",

    "pmax": "pmax",
    "precip_max": "pmax",
    "precipitacion_max": "pmax",
    "lluvia_max": "pmax",

    # humedad (rango)
    "hmin": "hmin",
    "hum_min": "hmin",
    "humedad_min": "hmin",

    "hmax": "hmax",
    "hum_max": "hmax",
    "humedad_max": "hmax",

    # óptimos centrales opcionales
    "p_opt": "p_opt",
    "precip_opt": "p_opt",
    "hum_opt": "h_opt",
    "h_opt": "h_opt",
    "tmed_opt": "tmed_opt",
}

def _parse_float(v):
    try:
        # Reemplaza coma por punto si el CSV trae comas decimales
        if isinstance(v, str):
            v = v.replace(",", ".").strip()
        return float(v)
    except Exception:
        return None

@lru_cache(maxsize=1)
def _cargar_tabla(csv_path: str | Path = None) -> Dict[str, Dict[str, float]]:
    """
    Devuelve un dict indexado por nombre de cultivo normalizado -> parámetros (dict).
    """
    path = Path(csv_path) if csv_path else CSV_PATH
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el CSV de condiciones: {path}")

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Normalizar nombres de columnas
        std_headers = {}
        for h in reader.fieldnames or []:
            key = _normalizar_texto(h)
            std_headers[h] = HEADER_MAP.get(key, key)  # deja el original si no está mapeado

        data: Dict[str, Dict[str, float]] = {}
        for row in reader:
            std_row = {}
            for orig_key, val in row.items():
                std_key = std_headers.get(orig_key, orig_key)
                std_row[std_key] = val

            nombre = _normalizar_texto(std_row.get("cultivo", ""))
            if not nombre:
                # fila sin cultivo, saltar
                continue

            params = {}
            # Campos que esperamos (si no existen, se quedan como None y se resolverán luego)
            for k in ["tmin", "tmax", "pmin", "pmax", "hmin", "hmax", "p_opt", "h_opt", "tmed_opt"]:
                params[k] = _parse_float(std_row.get(k))

            data[nombre] = params

    return data

# ---------------------
# API pública
# ---------------------
def get_optimos(cultivo: str, csv_path: str | Path = None) -> Dict[str, float]:
    """
    Devuelve los óptimos/rangos para el cultivo:
    keys: tmin, tmax, pmin, pmax, hmin, hmax, p_opt?, h_opt?, tmed_opt?
    Si p_opt, h_opt o tmed_opt no están en el CSV, se derivan como el punto medio de sus rangos.
    """
    tabla = _cargar_tabla(csv_path)
    nombre = _normalizar_texto(cultivo)
    if nombre not in tabla:
        raise KeyError(f"Cultivo '{cultivo}' no está en el CSV. Revisa nombres o acentos.")

    row = dict(tabla[nombre])  # copia
    # Derivar óptimos centrales si faltan
    if row.get("p_opt") is None and (row.get("pmin") is not None and row.get("pmax") is not None):
        row["p_opt"] = (row["pmin"] + row["pmax"]) / 2.0
    if row.get("h_opt") is None and (row.get("hmin") is not None and row.get("hmax") is not None):
        row["h_opt"] = (row["hmin"] + row["hmax"]) / 2.0
    if row.get("tmed_opt") is None and (row.get("tmin") is not None and row.get("tmax") is not None):
        row["tmed_opt"] = (row["tmin"] + row["tmax"]) / 2.0

    # Validaciones mínimas
    faltantes = [k for k in ["tmin", "tmax", "pmin", "pmax", "hmin", "hmax"] if row.get(k) is None]
    if faltantes:
        raise ValueError(f"Faltan columnas/valores en el CSV para '{cultivo}': {faltantes}")

    return row

def get_pesos(cultivo: str, fase: Optional[str] = None) -> Dict[str, float]:
    """
    Pesos recomendados por cultivo y fase. Si no se reconoce la fase, retorna preset general.
    Fases sugeridas: 'siembra', 'crecimiento', 'floracion', 'llenado', 'cosecha'
    """
    c = _normalizar_texto(cultivo)
    f = _normalizar_texto(fase) if fase else None

    # Preset por defecto (equilibrado con leve énfasis en tmed/precip)
    base = {"tmin": 0.18, "tmax": 0.18, "tmed": 0.24, "precip": 0.24, "hum": 0.16}

    # Ejemplos específicos (ajusta a tus cultivos)
    if "arroz" in c:
        if f in {"siembra", "establecimiento"}:
            return {"tmin": 0.10, "tmax": 0.10, "tmed": 0.30, "precip": 0.35, "hum": 0.15}
        if f in {"floracion", "llenado"}:
            return {"tmin": 0.10, "tmax": 0.20, "tmed": 0.25, "precip": 0.25, "hum": 0.20}
        return {"tmin": 0.12, "tmax": 0.18, "tmed": 0.28, "precip": 0.27, "hum": 0.15}

    if "maiz" in c or "maíz" in c:
        return {"tmin": 0.15, "tmax": 0.20, "tmed": 0.25, "precip": 0.25, "hum": 0.15}

    # Otros cultivos pueden agregarse aquí...

    return base

def get_config(cultivo: Optional[str] = None) -> Dict[str, float]:
    """
    Config por defecto; puedes personalizar por cultivo si lo necesitas.
    """
    return {
        "precip_deficit_tol": 0.20,  # 20% por debajo del óptimo => 0
        "hum_tolerancia": 0.10,      # ±10% sin penalizar
        "hum_rolloff": 0.50,         # caída suave fuera de la banda
        "temp_holgura_c": 5.0,       # holgura (°C) fuera del rango tmin/tmax
        "tmed_holgura_c": 3.0,       # holgura (°C) alrededor de la tmedia óptima
    }

def obtener_parametros(cultivo: str, fase: Optional[str] = None, csv_path: str | Path = None) -> Tuple[Dict, Dict, Dict]:
    """
    Atajo que regresa (optimos, pesos, config) listos para `calcular_probabilidad_avanzada`.
    """
    optimos = get_optimos(cultivo, csv_path=csv_path)
    pesos = get_pesos(cultivo, fase=fase)
    config = get_config(cultivo)
    return optimos, pesos, config
