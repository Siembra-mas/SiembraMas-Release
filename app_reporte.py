
# app_reporte.py — Blueprint para "Reportes"
from flask import Blueprint, render_template
bp = Blueprint("reporte", __name__)

@bp.route("/reporte")
def reporte():
    return render_template("reporte_sm.html")
