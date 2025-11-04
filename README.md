# Siembra+ Release

Aplicación web en **Flask** para predicción y recomendación de cultivos, potenciada con IA (Ollama + Vosk) para entrada de voz.

## ⚠️ PRE-REQUISITOS DEL SISTEMA PARA EL AGENTE DE VOZ (Windows y Linux)

Para el correcto funcionamiento del SiembraBot, el sistema necesita las siguientes herramientas instaladas globalmente:

| Componente | Motivo | Pasos de Configuración | Enlace de Descarga |
| :--- | :--- | :--- | :--- |
| **FFmpeg** | Necesario para que Python pueda convertir el audio grabado por el navegador (`.webm`) a un formato (`.wav`) que Vosk pueda entender. | **Linux:** `sudo apt install ffmpeg`. **Windows:** Descargar, descomprimir y añadir la ruta a la carpeta `bin` al `PATH` del sistema. |  |
| **Ollama** | Servidor de Lenguaje Grande (LLM) que procesa la transcripción de voz y extrae los parámetros de la siembra (Estado, Mes, Cultivo). | Instalar y asegurarse de que el comando `ollama serve` esté corriendo en segundo plano antes de iniciar Flask. |  |
| **Modelo Vosk (Grande)** | Diccionario acústico de alta precisión para la transcripción. El modelo "small" no es suficiente para oraciones complejas. | Descargar el modelo de español (128MB+) y colocar la carpeta en la raíz del proyecto. |  |

### 1. Preparación del Entorno Python

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/Siembra-mas/SiembraMas-Release.git](https://github.com/Siembra-mas/SiembraMas-Release.git)
    cd SiembraMas-Release
    ```

2.  **Crear y activar entorno virtual:**
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # Linux / macOS
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

### 2. Ejecución del Proyecto

1.  **Descargar y Cargar el Modelo Gemma:**
    ```bash
    ollama pull gemma:2b
    ```

2.  **Iniciar Ollama Server:**
    Asegúrese de que el servidor de IA esté activo en una terminal separada:
    ```bash
    ollama serve
    ```

3.  **Ejecutar la aplicación Flask:**
    ```bash
    python app.py
    ```

4.  Abrir en el navegador:
    ```
    [http://127.0.0.1:5000](http://127.0.0.1:5000)
    ```

## 🎙️ Instrucciones del SiembraBot

1.  **Uso:** Haga clic en el botón SiembraBot, diga su consulta completa (ej: "Quiero sembrar maíz en Guanajuato en diciembre"), y haga clic de nuevo para detener.
2.  **Resultado:** El bot rellenará los campos, enviará la solicitud al servidor, y **hablará** los resultados del análisis.
