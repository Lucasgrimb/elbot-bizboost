import logging
from flask import current_app, jsonify
import json
import requests

from app.services.langchain_service import generate_response
import re


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
            "status": "read",
            "message_id": message_id,  # Message ID to mark as read
            "to": wa_id  # WhatsApp ID of the recipient
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
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    message_body = message["text"]["body"]
    message_id = message["id"]  # Message ID for marking as read

    # OpenAI Integration
    response = generate_response(message_body, wa_id, name)
    response = process_text_for_whatsapp(response)

    # Send the response message
    data = get_text_message_input(wa_id, response)
    send_message(data)

    # Send the read receipt to mark the message as read
    send_read_receipt(message_id, wa_id)


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

    # Payload for the template message
    data = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }

    # Add components if provided
    if components:
        data["template"]["components"] = components

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        logging.info(f"Template message sent to {recipient}.")
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Failed to send template message to {recipient}: {e}")
        return None




