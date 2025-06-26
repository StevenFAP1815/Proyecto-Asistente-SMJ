import sys
import os
from dotenv import load_dotenv
import logging

def load_configurations(app):
    """Carga variables de entorno y configura el diccionario app.config"""
    load_dotenv(override=True)

    # Variables esenciales para autenticación y funcionamiento
    app.config["ACCESS_TOKEN"] = os.getenv("ACCESS_TOKEN")
    app.config["MY_NUMBER"] = os.getenv("MY_NUMBER")
    app.config["APP_ID"] = os.getenv("APP_ID")
    app.config["APP_SECRET"] = os.getenv("APP_SECRET")
    app.config["TEST_NUMBER_META"] = os.getenv("TEST_NUMBER_META")
    app.config["VERSION"] = os.getenv("VERSION")
    app.config["TEST_NUMBER_ID"] = os.getenv("TEST_NUMBER_ID")
    app.config["ID_WHATSAPP_BUSSINES"] = os.getenv("ID_WHATSAPP_BUSSINES")

    # Claves de OpenAI
    app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    app.config["OPENAI_ASSISTANT_ID"] = os.getenv("OPENAI_ASSISTANT_ID")

    # Configuración de base de datos
    app.config["DB_USER"] = os.getenv("DB_USER")
    app.config["DB_PASSWORD"] = os.getenv("DB_PASSWORD")
    app.config["DB_HOST"] = os.getenv("DB_HOST")
    app.config["DB_PORT"] = os.getenv("DB_PORT")
    app.config["DB_NAME"] = os.getenv("DB_NAME")

    # Validación de variables obligatorias
    required_keys = [
        "ACCESS_TOKEN", "OPENAI_API_KEY",
        "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"
    ]
    missing_keys = [key for key in required_keys if not app.config.get(key)]
    if missing_keys:
        raise RuntimeError(f"Faltan variables de entorno obligatorias: {', '.join(missing_keys)}")

def configure_logging():
    """Configura logging con formato estándar"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
