
# app_disp_monit.py — Blueprint para "Dispositivos y Monitoreo"
from flask import Blueprint, render_template
bp = Blueprint("disp_monit", __name__)

@bp.route("/disp-monit")
def disp_monit():
    return render_template("disp-monit_sm.html")
