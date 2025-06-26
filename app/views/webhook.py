import logging
import json

from flask import Blueprint, request, jsonify, current_app

from app.utils.decorators import firma_requerida
from app.utils.whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)

webhook_blueprint = Blueprint("webhook", __name__)


def handle_message():

    body = request.get_json()
    # logging.info(f"request body: {body}")

    # Verifica si el evento es un mensaje de WhatsApp
    if (
        body.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses")
    ):
        logging.info("Reciví un evento/actualización de estado de WhatsApp")
        return jsonify({"status": "ok"}), 200

    try:
        if is_valid_whatsapp_message(body):
            process_whatsapp_message(body)
            return jsonify({"status": "ok"}), 200
        else:
            # Si la solicitud no es un mensaje de WhatsApp válido, devuelve un error 404
            return (
                jsonify({"status": "error", "message": "No es un evento de WhatsApp válido"}),
                404,
            )
    except json.JSONDecodeError:
        logging.error("Fallo al decodificar el JSON")
        # Si la carga útil no es un JSON válido, devuelve un error 400
        return jsonify({"status": "error", "message": "JSON proporcionado no válido"}), 400


# Requiere el token de verificación para la verificación del webhook
def verify():
    # Analiza los parámetros de la solicitud de verificación del webhook
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    # Verifica si un token de verificación y un modo fueron enviados
    if mode and token:
        # Verifica si el modo y el token son correctos
        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]: #Paraque el servidor interactúe con la API de WhatsApp Business, se debe verificar el webhook con un token de verificación.
            # Responde con 200 si el token de verificación es correcto
            logging.info("WEBHOOK VERIFICADO")
            return challenge, 200
        else:
            # Responde con '403 Forbidden' si el token de verificación no es correcto
            logging.info("VERIFICACION FALLIDA")
            return jsonify({"status": "error", "message": "Verificación fallida"}), 403
    else:
        # Responde con 400 si faltan parámetros
        logging.info("FALTAN PARAMETROS")
        return jsonify({"status": "error", "message": "Faltan parámetros"}), 400

#Para manejar las solicitudes GET y POST al webhook
# GET: Para verificar el webhook con el token de verificación
@webhook_blueprint.route("/webhook", methods=["GET"])
def webhook_get():
    return verify()
# POST: Para recibir mensajes de WhatsApp y otros eventos
@webhook_blueprint.route("/webhook", methods=["POST"])
@firma_requerida
def webhook_post():
    return handle_message()