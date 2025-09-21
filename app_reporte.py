# app_reporte.py
# Blueprint para la página de reportes (reporte_sm.html)
from flask import Blueprint, render_template, request, jsonify

bp = Blueprint(
    "reporte",
    __name__,
    url_prefix="/reporte",
)

@bp.get("")
@bp.get("/")
def pagina_reporte():
    """
    Renderiza la página de reportes.
    - Asegúrate de tener templates/reporte_sm.html
    """
    return render_template("reporte_sm.html")

@bp.post("/generar")
def generar_reporte():
    """
    Endpoint de ejemplo para generar/descargar reportes.
    Reemplaza con tu lógica real (pandas, gráficos, PDF, etc.).
    """
    filtros = request.get_json(silent=True) or request.form
    # TODO: generar reporte real con filtros
    resumen = {"total_cultivos": 12, "mejor_estacion": "Primavera"}
    return jsonify({"ok": True, "resumen": resumen})
