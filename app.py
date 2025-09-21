
# app.py — punto de entrada principal (main)
from flask import Flask
from app_inicio import bp as inicio_bp
from app_about import bp as about_bp
from app_disp_monit import bp as disp_bp
from app_reporte import bp as reporte_bp

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    # Registra blueprints
    app.register_blueprint(inicio_bp)                # "/" y "/generar"
    app.register_blueprint(about_bp, url_prefix="")  # "/about"
    app.register_blueprint(disp_bp, url_prefix="")   # "/disp-monit"
    app.register_blueprint(reporte_bp, url_prefix="")# "/reporte"
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
