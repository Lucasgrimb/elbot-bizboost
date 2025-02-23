import logging
from flask import current_app, jsonify
import json
import requests
import importlib
#from app.services.langchain_service import generate_response
import re

PHONE_NUMBER_TO_MODULE = {
    "5491151465950": "app.services.langchain_jelko",
    "5491136148233": "app.services.langchain_jelko",
}

def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except requests.RequestException as e:
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        log_http_response(response)
        return response


def send_read_receipt(message_id, wa_id):
    """
    Sends a read receipt to WhatsApp indicating the message has been read.
    """
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    # Payload for marking the message as read
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "status": "read",  # Indica que el mensaje ha sido leído
            "message_id": message_id,  # ID del mensaje recibido
            "to": wa_id  # WhatsApp ID del remitente
        }
    )

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        logging.error("Timeout occurred while sending read receipt")
    except requests.RequestException as e:
        logging.error(f"Request failed while sending read receipt due to: {e}")
    else:
        log_http_response(response)



def process_text_for_whatsapp(text):
    pattern = r"\【.*?\】"
    text = re.sub(pattern, "", text).strip()

    pattern = r"\*\*(.*?)\*\*"
    replacement = r"*\1*"
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text




def process_whatsapp_message(body):
    # Obtener el número del destinatario
    phone_number = body["entry"][0]["changes"][0]["value"]["metadata"]["display_phone_number"]

    # Buscar el módulo correspondiente al número de teléfono
    module_name = PHONE_NUMBER_TO_MODULE.get(phone_number)
    if not module_name:
        logging.error(f"No module found for phone number: {phone_number}")
        return

    # Cargar dinámicamente el módulo
    try:
        company_module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        logging.error(f"Module {module_name} not found for phone number: {phone_number}")
        return

    # Obtener la función generate_response del módulo
    generate_response = getattr(company_module, "generate_response", None)
    if not callable(generate_response):
        logging.error(f"Function 'generate_response' not found in module {module_name}")
        return

    # Extraer datos del mensaje
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
    message_data = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_id = message_data["id"]  # ID del mensaje

    # Enviar recibo de lectura
    send_read_receipt(message_id, wa_id)

    # Verificar si el mensaje es de audio
    if message_data["type"] == "audio":
        response_text = "Hola! Si podes haceme el favor de escribirme, no puedo escuchar audios."
    else:
        # Generar la respuesta normal
        message = message_data["text"]["body"]
        response_text = generate_response(message, wa_id, name)

    # Enviar la respuesta
    data = get_text_message_input(wa_id, response_text)
    send_message(data)





def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )



import requests
import logging
from flask import current_app

import requests
import logging
from flask import current_app

def send_template_message(recipient, template_name, language_code="es", components=None):
    """
    Send a proactive WhatsApp message using a pre-approved template.

    Args:
        recipient (str): The WhatsApp ID of the recipient (e.g., phone number with country code).
        template_name (str): The name of the approved WhatsApp template.
        language_code (str): The language code of the template (default is 'es').
        components (list): Components for the template placeholders (default is None).
    """
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    # Payload para el mensaje de plantilla
    data = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code}
        }
    }
    
    # Solo agregar "components" si se proporciona correctamente
    if components:
        if isinstance(components, list):  # Verifica que sea una lista
            data["template"]["components"] = components
        else:
            print("⚠️ Error: 'components' no es una lista de objetos JSON válida.")
            return None  # No continuar si hay un error en los components

    print(f"Payload corregido: {data}")  # Imprime el JSON antes de enviarlo

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"Respuesta HTTP: {response.status_code}, {response.text}")  # Imprime la respuesta exacta
        response.raise_for_status()
        logging.info(f"Template message sent to {recipient}.")
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to send template message to {recipient}: {e}")
        print(f"Error enviando mensaje: {e}")  # Muestra el error en consola
        if response is not None:
            print(f"Respuesta de WhatsApp: {response.text}")  # Muestra detalles del error si hay respuesta
        return None



