# app.py
from flask import Flask, render_template, request, jsonify, url_for
import unicodedata, re
import pandas as pd

# === Importar tus módulos (no se modifican) ===
import Prediccion  # usa Prediccion.Prediccion(...), predice 2025 y devuelve Pred_TempMin / Pred_tempMax  :contentReference[oaicite:6]{index=6}
from Cultivos import obtener_cultivos  # lee CSV y agrupa cultivos por entidad  :contentReference[oaicite:7]{index=7}

# Catálogos (nombre del archivo puede variar; intentamos ambos)
try:
    from Catalogos import estados, municipios, Lugar, coordenadas, coordenadas_municipios
except Exception:
    from catalogo import estados, municipios, Lugar, coordenadas, coordenadas_municipios

app = Flask(__name__, template_folder="templates", static_folder="static")

# ---------------- Utilidades ----------------
def normalizar_texto(texto: str) -> str:
    if not isinstance(texto, str):
        return texto
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto.upper()

def slug_cultivo(nombre: str) -> str:
    """crea un slug coherente para nombre de imagen a partir del cultivo."""
    s = unicodedata.normalize('NFD', nombre).encode('ascii', 'ignore').decode('utf-8')
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s.strip().lower())
    s = re.sub(r'-+', '-', s).strip('-')
    return s  # p.ej. "Tomate rojo (jitomate)" -> "tomate-rojo-jitomate"

MESES = [
    "Todos",
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]
ANIOS = [2025]  # tu función hoy genera 2025  :contentReference[oaicite:8]{index=8}

def nearest_by_coords(lat, lon, pool_dict):
    best_key, best_d = None, 10**9
    for k, (la, lo) in pool_dict.items():
        d = (la - lat)**2 + (lo - lon)**2
        if d < best_d:
            best_key, best_d = k, d
    return best_key

# ---------------- Rutas ----------------
@app.route("/", methods=["GET"])
def home():
    context = dict(
        ruta_opciones=Lugar,
        estados=estados,
        municipios=municipios,
        meses=MESES,
        anios=ANIOS,
        ruta_sel="Estados",
        estado_sel="",
        municipio_sel="",
        mes_sel="Todos",
        anio_sel=ANIOS[0],
        temp_max=None, temp_min=None, temp_media=None,
        precipitacion=None, humedad=None,
        nombre_mes=None,
        recomendaciones=[]  # lista de tarjetas a pintar
    )
    return render_template("inicio_sm.html", **context)

@app.route("/ubicarme", methods=["POST"])
def ubicarme():
    data = request.get_json(force=True)
    lat = float(data.get("lat"))
    lon = float(data.get("lon"))
    municipio_cercano = nearest_by_coords(lat, lon, coordenadas_municipios) if 'coordenadas_municipios' in globals() else None
    if municipio_cercano:
        return jsonify({"ruta": "Municipios", "lugar": municipio_cercano})
    estado_cercano = nearest_by_coords(lat, lon, coordenadas)
    return jsonify({"ruta": "Estados", "lugar": estado_cercano})

@app.route("/generar", methods=["POST"])
def generar():
    ruta = request.form.get("ruta") or "Estados"     # "Estados" | "Municipios"
    estado = request.form.get("estado") or ""
    municipio = request.form.get("municipio") or ""
    mes_texto = request.form.get("mes") or "Todos"
    anio = int(request.form.get("anio") or 2025)

    # Determinar lugar según la ruta elegida (misma idea de tu Main.py)  :contentReference[oaicite:9]{index=9}
    if ruta == "Estados":
        lugar = estado
        ruta_csv_cultivos = "./Ideal/CultivoEstado.csv"
    else:
        lugar = municipio
        ruta_csv_cultivos = "./Ideal/CultivoMunicipio.csv"

    # Mes solicitado: entero 1..12 o None
    mes_solicitado = MESES.index(mes_texto) if mes_texto and mes_texto != "Todos" else None

    temp_max = temp_min = temp_media = None
    nombre_mes = None

    # --- 1) Temperaturas (usa tu función tal cual)  :contentReference[oaicite:10]{index=10}
    if ruta and lugar:
        df = Prediccion.Prediccion(ruta=ruta, lugar=lugar, mes_solicitado=mes_solicitado, Cultivo=None)
        if not df.empty:
            row = df.iloc[0]
            temp_min = float(row["Pred_TempMin"])
            temp_max = float(row["Pred_tempMax"])
            temp_media = round((temp_min + temp_max) / 2.0, 2)
            nombre_mes = row.get("Nombre_Mes", None)

    precipitacion = None
    humedad = None

    # --- 2) Recomendaciones de cultivos (estructura de tarjetas) ---
    recomendaciones = []
    try:
        # cultivos por entidad/municipio  :contentReference[oaicite:11]{index=11}
        dic_cultivos = obtener_cultivos(ruta_csv_cultivos)
        dic_norm = {normalizar_texto(k): v for k, v in dic_cultivos.items()}
        lista_cultivos = dic_norm.get(normalizar_texto(lugar), []) if lugar else []

        # condiciones ideales por cultivo (para mensaje/probabilidad)  :contentReference[oaicite:12]{index=12}
        condiciones = pd.read_csv("./CondicionesIdeales/CondicionesIdeales.csv", encoding="utf-8")
        condiciones["Cultivo_normalizado"] = condiciones["Cultivo"].apply(normalizar_texto)

        def calcular_probabilidad(temp_min_pred, temp_max_pred, tmin_ok, tmax_ok):
            # misma idea que Main.py: cuán cerca del rango ideal  :contentReference[oaicite:13]{index=13}
            rango = (tmin_ok, tmax_ok)
            dentro_min = max(0, min(1, (temp_max_pred - rango[0]) / (rango[1] - rango[0])))
            dentro_max = max(0, min(1, (rango[1] - temp_min_pred) / (rango[1] - rango[0])))
            return round(((dentro_min + dentro_max) / 2) * 100, 1)

        for cultivo in lista_cultivos:
            # Predicción específica para el cultivo (tu función la acepta; no se modifica)  :contentReference[oaicite:14]{index=14}
            df_c = Prediccion.Prediccion(ruta=ruta, lugar=lugar, mes_solicitado=mes_solicitado, Cultivo=cultivo)
            if df_c.empty:
                continue
            r0 = df_c.iloc[0]
            tmin_pred = float(r0["Pred_TempMin"])
            tmax_pred = float(r0["Pred_tempMax"])

            # condiciones ideales de este cultivo
            c_norm = normalizar_texto(cultivo)
            cond = condiciones[condiciones["Cultivo_normalizado"] == c_norm]
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
                prob = None
                texto = f"No hay condiciones registradas para {cultivo}"

            recomendaciones.append({
                "cultivo": cultivo,
                "prob": prob,
                "texto": texto,
                "img_slug": slug_cultivo(cultivo)  # para mostrar imagen coherente
            })
    except Exception:
        # Si faltan CSVs, la sección quedará vacía sin romper la página
        recomendaciones = []

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
        recomendaciones=recomendaciones
    )
    return render_template("inicio_sm.html", **context)

if __name__ == "__main__":
    app.run(debug=True)
