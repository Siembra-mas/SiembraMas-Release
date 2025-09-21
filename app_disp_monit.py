# app_disp_monit.py
# Blueprint para la página de dispositivos/monitoreo (disp-monit_sm.html)
from flask import Blueprint, render_template, request, jsonify

bp = Blueprint(
    "dispositivos",
    __name__,
    url_prefix="/dispositivos",
)

@bp.get("")
@bp.get("/")
def pagina_dispositivos():
    """
    Renderiza la página de dispositivos/monitoreo.
    - Asegúrate de tener templates/disp-monit_sm.html
    """
    return render_template("disp-monit_sm.html")

@bp.post("/datos")
def api_datos_dispositivos():
    """
    Endpoint de ejemplo para alimentar gráficos/tablas en la vista.
    Sustituye con tu lógica (lectura de sensores, DB, etc.).
    """
    # payload = request.get_json(silent=True) or request.form
    data = [
        {"id": "sensor-01", "temp": 23.1, "hum": 62},
        {"id": "sensor-02", "temp": 24.3, "hum": 58},
    ]
    return jsonify({"ok": True, "data": data})
