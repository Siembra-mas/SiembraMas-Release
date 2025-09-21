
# app_about.py — Blueprint para la página "Acerca de"
from flask import Blueprint, render_template
bp = Blueprint("about", __name__)

@bp.route("/about")
def about():
    return render_template("about_sm.html")
