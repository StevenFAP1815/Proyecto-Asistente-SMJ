from flask import current_app, jsonify
import json
import os
import requests
import re
import logging
import mimetypes
from typing import Optional, Dict, Any

try:
    from app.services.assistant_instance import assistant_manager_instance as assistant
except ImportError as e:
    logging.error(f"Error importando assistant_manager_instance: {e}")
    assistant = None

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_http_response(response):
    """Log de respuesta HTTP con manejo seguro de contenido"""
    try:
        logging.info(f"Status: {response.status_code}")
        logging.info(f"Content-type: {response.headers.get('content-type', 'unknown')}")
        # Manejo seguro del texto de respuesta
        body_text = response.text[:200] if hasattr(response, 'text') else 'No content'
        logging.info(f"Body: {body_text}...")
    except Exception as e:
        logging.error(f"Error logging response: {e}")

def get_text_message_input(recipient: str, text: str) -> str:
    """Genera el JSON para mensaje de texto con validación"""
    if not recipient or not text:
        raise ValueError("Recipient y text son requeridos")
    
    return json.dumps({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": False, "body": text}
    })

def get_required_config(key: str) -> str:
    """Obtiene configuración requerida con manejo de errores"""
    try:
        value = current_app.config.get(key)
        if not value:
            raise ValueError(f"Configuración {key} no encontrada o vacía")
        return value
    except RuntimeError:
        raise RuntimeError(f"No hay contexto de aplicación Flask para obtener {key}")

def send_message(data: str) -> Optional[requests.Response]:
    """Envía mensaje con manejo robusto de errores y configuración"""
    try:
        headers = {
            "Content-type": "application/json",
            "Authorization": f"Bearer {get_required_config('ACCESS_TOKEN')}"
        }

        version = get_required_config('VERSION')
        phone_id = get_required_config('PHONE_NUMBER_ID')
        url = f"https://graph.facebook.com/{version}/{phone_id}/messages"

        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        log_http_response(response)
        return response
        
    except ValueError as e:
        logging.error(f"Error de configuración: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error al enviar mensaje: {e}")
        return None
    except Exception as e:
        logging.error(f"Error inesperado enviando mensaje: {e}")
        return None

def process_text_for_whatsapp(text: str) -> str:
    """Procesa texto para WhatsApp con validación de entrada"""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    
    # Eliminar caracteres Unicode problemáticos de manera más segura
    text = re.sub(r"[\uff3b\uff3d]", "", text).strip()
    
    # Formato de markdown a WhatsApp
    text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)
    
    return text

def safe_get_nested_value(data: Dict[Any, Any], path: list, default=None):
    """Obtiene valores anidados de manera segura"""
    try:
        current = data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
                current = current[key]
            else:
                return default
        return current
    except (TypeError, KeyError, IndexError):
        return default

def process_whatsapp_message(body: Dict[Any, Any]):
    """Procesa mensaje de WhatsApp con validación robusta"""
    if not is_valid_whatsapp_message(body):
        return jsonify({"status": "error", "message": "Mensaje no válido"}), 400

    if not assistant:
        logging.error("Assistant no disponible")
        return jsonify({"status": "error", "message": "Servicio no disponible"}), 503

    try:
        # Extracción segura de datos usando helper function
        contacts_path = ["entry", 0, "changes", 0, "value", "contacts", 0]
        messages_path = ["entry", 0, "changes", 0, "value", "messages", 0]
        
        contact = safe_get_nested_value(body, contacts_path, {})
        message = safe_get_nested_value(body, messages_path, {})
        
        wa_id = contact.get("wa_id")
        name = safe_get_nested_value(contact, ["profile", "name"], "Cliente")
        
        if not wa_id:
            logging.error("wa_id no encontrado en el mensaje")
            return jsonify({"status": "error", "message": "ID de usuario no válido"}), 400

        if message.get("type") != "text":
            logging.info(f"Tipo de mensaje no soportado: {message.get('type')}")
            return jsonify({"status": "ignored", "message": "Tipo no soportado"}), 200

        message_body = safe_get_nested_value(message, ["text", "body"], "")
        
        if not message_body:
            logging.warning("Mensaje vacío recibido")
            return jsonify({"status": "ignored", "message": "Mensaje vacío"}), 200

        # Generar respuesta del asistente
        try:
            response = assistant.generate_response(
                message_body=message_body,
                wa_id=wa_id,
                name=name
            )
        except Exception as e:
            logging.error(f"Error generando respuesta del asistente: {e}")
            response = "Lo siento, ocurrió un error procesando tu mensaje."

        if not response:
            logging.warning("Assistant devolvió respuesta vacía")
            response = "Lo siento, no pude generar una respuesta."

        formatted_response = process_text_for_whatsapp(response)
        message_data = get_text_message_input(wa_id, formatted_response)
        
        send_result = send_message(message_data)
        
        if send_result:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error", "message": "Error enviando mensaje"}), 500

    except Exception as e:
        logging.error(f"Error en process_whatsapp_message: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Error interno del servidor"}), 500

def is_valid_whatsapp_message(body: Dict[Any, Any]) -> bool:
    """Validación robusta de estructura de mensaje WhatsApp"""
    if not isinstance(body, dict):
        return False
    
    required_paths = [
        ["object"],
        ["entry", 0, "changes", 0, "value", "messages", 0],
        ["entry", 0, "changes", 0, "value", "contacts", 0, "wa_id"]
    ]
    
    for path in required_paths:
        if safe_get_nested_value(body, path) is None:
            logging.warning(f"Estructura de mensaje inválida: falta {' -> '.join(map(str, path))}")
            return False
    
    return True

def upload_media(filepath: str) -> Optional[str]:
    """Sube media con detección automática de tipo y validación"""
    if not filepath or not os.path.exists(filepath):
        logging.error(f"Archivo no encontrado: {filepath}")
        return None
    
    # Detectar tipo MIME automáticamente
    mime_type, _ = mimetypes.guess_type(filepath)
    if not mime_type:
        mime_type = "application/octet-stream"
    
    try:
        version = get_required_config('VERSION')
        phone_id = get_required_config('PHONE_NUMBER_ID')
        access_token = get_required_config('ACCESS_TOKEN')
        
        url = f"https://graph.facebook.com/{version}/{phone_id}/media"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        with open(filepath, "rb") as file:
            files = {"file": (os.path.basename(filepath), file, mime_type)}
            response = requests.post(url, headers=headers, files=files, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result.get("id")
            
    except Exception as e:
        logging.error(f"Error al subir media: {e}")
        return None

def send_image_message(recipient: str, image_url: str, caption: str = "") -> Optional[Dict]:
    """Envía mensaje de imagen con validación"""
    if not recipient or not image_url:
        logging.error("Recipient e image_url son requeridos")
        return None
    
    try:
        version = get_required_config('VERSION')
        phone_id = get_required_config('PHONE_NUMBER_ID')
        access_token = get_required_config('ACCESS_TOKEN')
        
        url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "image",
            "image": {"link": image_url, "caption": caption}
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logging.error(f"Error al enviar imagen: {e}")
        return None