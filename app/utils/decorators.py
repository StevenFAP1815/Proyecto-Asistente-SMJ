from functools import wraps
from flask import current_app, jsonify, request
import logging
import hashlib
import hmac

def validacion_firma(payload, firma):
    """
    Valida la firma HMAC-SHA256 del payload contra la firma recibida.
    
    Args:
        payload (str): Cuerpo de la solicitud en formato string.
        firma (str): Firma recibida en el header (sin el prefijo 'sha256=').
    
    Returns:
        bool: True si la firma es válida, False en caso contrario.
    """
    # Verificar que APP_SECRET esté configurada
    app_secret = current_app.config.get("APP_SECRET")
    if not app_secret:
        logging.error("APP_SECRET no está configurada")
        return False

    try:
        # Generar la firma esperada
        firma_esperada = hmac.new(
            app_secret.encode('latin-1'),  # Codificación explícita a bytes
            msg=payload.encode('utf-8'),    # Payload como bytes
            digestmod=hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(firma_esperada, firma)
    
    except Exception as e:
        logging.error(f"Error en validación de firma: {str(e)}")
        return False

def firma_requerida(f):
    """
    Decorador para validar solicitudes entrantes al webhook.
    
    Verifica que la firma X-Hub-Signature-256 coincida con la firma generada
    usando APP_SECRET. Si falla, retorna error 403.
    """
    @wraps(f)
    def funcion_decorada(*args, **kwargs):
        # Extraer firma del header (quitando 'sha256=')
        firma_header = request.headers.get("X-Hub-Signature-256", "")
        firma = firma_header[7:] if firma_header.startswith('sha256=') else ""
        
        if not firma:
            logging.warning("Header X-Hub-Signature-256 faltante o mal formado")
            return jsonify({"status": "error", "message": "Firma no proporcionada"}), 403
        
        try:
            payload = request.data.decode('utf-8')
        except UnicodeDecodeError:
            logging.warning("Payload no es UTF-8 válido")
            return jsonify({"status": "error", "message": "Payload inválido"}), 400

        if not validacion_firma(payload, firma):
            logging.warning(f"Firma inválida. Header: {firma_header}")
            return jsonify({"status": "error", "message": "Firma inválida"}), 403
            
        return f(*args, **kwargs)
    
    return funcion_decorada