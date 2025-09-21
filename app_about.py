# app_about.py
# Blueprint para la página "Acerca de" (about_sm.html)
from flask import Blueprint, render_template

bp = Blueprint(
    "about",
    __name__,
    url_prefix="/about",
)

@bp.get("")
@bp.get("/")
def pagina_about():
    """
    Renderiza la página "Acerca de".
    - Asegúrate de tener templates/about_sm.html
    """
    return render_template("about_sm.html")
