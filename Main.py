import streamlit as st
import Prediccion
from Catalogos import *
from Cultivos import obtener_cultivos
import pandas as pd
import unicodedata

#Función para normalizar acentos y mayúsculas
def normalizar_texto(texto: str) -> str:
    if not isinstance(texto, str):
        return texto
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto.upper()

st.set_page_config(page_title="Siembra +", layout="wide")
st.title("Siembra +")
st.sidebar.title("Configuración de Predicción")

meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# Selección de ruta de datos: Estado o Municipio
ruta = st.sidebar.selectbox("Ruta de Datos", Lugar)
if ruta == "Estados":
    lugar = st.sidebar.selectbox("Selecciona un Estado", estados)
    ruta_csv_cultivos = "./Ideal/CultivoEstado.csv"
else:
    lugar = st.sidebar.selectbox("Selecciona un Municipio", municipios)
    ruta_csv_cultivos = "./Ideal/CultivoMunicipio.csv"

#Selección de Mes
mes_texto = st.sidebar.selectbox("Selecciona un Mes", ["Todos"] + meses)
mes = meses.index(mes_texto) + 1 if mes_texto != "Todos" else None

#Cargar cultivos desde CSV y obtener opciones según el lugar
Cultivos = obtener_cultivos(ruta_csv_cultivos)

#Normalizar llaves del diccionario
Cultivos_normalizados = {normalizar_texto(k): v for k, v in Cultivos.items()}

# Buscar el lugar normalizado
opciones_cultivos = Cultivos_normalizados.get(normalizar_texto(lugar), [])

# Normalizar también cultivos en el selectbox
opciones_cultivos_normalizadas = [normalizar_texto(c) for c in opciones_cultivos]

# Mostrar selectbox con cultivos normalizados
Cultivo_normalizado = st.sidebar.selectbox("Selecciona un Cultivo", opciones_cultivos_normalizadas)

# Recuperar el cultivo original (para comparar con CSV de condiciones)
if Cultivo_normalizado in opciones_cultivos_normalizadas:
    idx = opciones_cultivos_normalizadas.index(Cultivo_normalizado)
    Cultivo = opciones_cultivos[idx]
else:
    Cultivo = None

# Ejecutar predicción
if ruta and lugar and Cultivo:
    resultados = Prediccion.Prediccion(ruta=ruta, lugar=lugar, mes_solicitado=mes, Cultivo=Cultivo)

    # Evaluar probabilidad de siembra
    condiciones = pd.read_csv("./CondicionesIdeales/CondicionesIdeales.csv")
    condiciones["Cultivo_normalizado"] = condiciones["Cultivo"].apply(normalizar_texto)
    cond = condiciones[condiciones["Cultivo_normalizado"] == normalizar_texto(Cultivo)]

    if not cond.empty:
        temp_min = cond["Temp min optima"].iloc[0]
        temp_max = cond["Temp max optima"].iloc[0]

        def calcular_probabilidad(temp_min_pred, temp_max_pred):
            """Devuelve porcentaje de cuán cerca está el rango predicho del rango ideal"""
            rango_ideal = (temp_min, temp_max)
            dentro_min = max(0, min(1, (temp_max_pred - rango_ideal[0]) / (rango_ideal[1] - rango_ideal[0])))
            dentro_max = max(0, min(1, (rango_ideal[1] - temp_min_pred) / (rango_ideal[1] - rango_ideal[0])))
            return round(((dentro_min + dentro_max) / 2) * 100, 1)

        def evaluar_fila(row):
            prob = calcular_probabilidad(row["Pred_TempMin"], row["Pred_tempMax"])
            if prob >= 70:
                return f"✅ Alta probabilidad ({prob}%) de siembra de {Cultivo}"
            elif prob >= 40:
                return f"⚠️ Posible siembra ({prob}%) de {Cultivo}"
            else:
                return f"❌ No conviene ({prob}%) de siembra de {Cultivo}"

        resultados["Recomendacion"] = resultados.apply(evaluar_fila, axis=1)
    else:
        resultados["Recomendacion"] = "No hay condiciones registradas para este cultivo"

    # Mostrar resultados
    st.subheader(f"Predicción y recomendación de siembra para {Cultivo} en {lugar}")
    if mes:
        st.write(f"Mostrando resultados solo para el mes {mes} ({mes_texto}) en 2025:")
    else:
        st.write("Mostrando predicciones de todos los meses para 2025:")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(resultados[['Año', 'Nombre_Mes', 'Pred_TempMin', 'Pred_tempMax', 'Recomendacion']],
                     use_container_width=True, hide_index=True)
    with col2:
        if lugar in coordenadas:
            lat, lon = coordenadas[lugar]
            df_map = pd.DataFrame([[lat, lon]], columns=["lat", "lon"])
            st.map(df_map, zoom=5, use_container_width=True)
        else:
            st.info("No hay coordenadas disponibles para este lugar.")

    st.write("Nota: Los datos se han procesado y las predicciones se han realizado utilizando un modelo de Random Forest.")
