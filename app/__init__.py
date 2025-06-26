from flask import Flask
from app.config.config_loader import load_configurations, configure_logging
from app.database.db_connection import init_engine_from_config, close_db_connection
from app.views.webhook import webhook_blueprint

def create_app():
    app = Flask(__name__)

    # Cargar variables de configuración y logging
    load_configurations(app)
    configure_logging()

    # Inicializar conexión a la base de datos al arrancar la app
    with app.app_context():
        init_engine_from_config()

    # Cerrar sesión de base de datos al terminar cada request
    app.teardown_appcontext(close_db_connection)

    # Registrar rutas (blueprints)
    app.register_blueprint(webhook_blueprint)

    return app
