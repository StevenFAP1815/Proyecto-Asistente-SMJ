from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from flask import current_app, g
import logging

# Variables globales
engine = None
SessionFactory = None


def init_engine_from_config():
    """
    Inicializa el motor SQLAlchemy y el SessionFactory.
    Debe ser llamada explícitamente al inicio de la aplicación Flask (en create_app).
    """
    global engine, SessionFactory

    if engine is not None:
        return  # Ya inicializado

    try:
        db_url = (
            f"mysql+mysqlconnector://{current_app.config['DB_USER']}:"
            f"{current_app.config['DB_PASSWORD']}@"
            f"{current_app.config['DB_HOST']}:{current_app.config['DB_PORT']}/"
            f"{current_app.config['DB_NAME']}"
        )
        engine = create_engine(db_url, pool_pre_ping=True)
        SessionFactory = scoped_session(sessionmaker(bind=engine))
        logging.info("Motor de base de datos inicializado correctamente.")
    except Exception as e:
        logging.error(f"Error al inicializar motor de base de datos: {e}", exc_info=True)
        raise


def get_db_connection():
    """
    Retorna una sesión de base de datos válida dentro del contexto Flask.
    Requiere que `init_engine_from_config()` haya sido llamado previamente.
    """
    if SessionFactory is None:
        raise RuntimeError("El motor de base de datos no ha sido inicializado. "
                    "Llama a init_engine_from_config() en create_app().")

    if not hasattr(g, "db_session"):
        g.db_session = SessionFactory()
    return g.db_session


def close_db_connection(error=None):
    """
    Cierra la sesión de base de datos después de cada solicitud.
    """
    if hasattr(g, "db_session"):
        SessionFactory.remove()
        logging.debug("Sesión de base de datos eliminada del contexto.")
