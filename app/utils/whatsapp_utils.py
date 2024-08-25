import logging
from flask import current_app, jsonify
import json
import requests
import re
from app.services.langchain_service import generate_response
import openai
import os
import io

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


def download_audio_file(media_id):
    """
    Download the audio file from WhatsApp servers using the media_id.
    """
    url = f"https://graph.facebook.com/v12.0/{media_id}"
    headers = {
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        media_url = response.json().get("url")
        audio_data = requests.get(media_url, headers=headers)
        if audio_data.status_code == 200:
            return audio_data.content  # Returns the audio file content
    logging.error("Failed to download audio")
    return None


def transcribe_audio(audio_content):
    """
    Transcribe the audio content using Whisper with the new OpenAI API.
    """
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    try:
        # Crear un archivo simulado en memoria desde el contenido binario
        audio_file = io.BytesIO(audio_content)
        audio_file.name = "audio_message.mp3"  # Debe tener un nombre válido
        
        # Llamar a la API con el archivo
        response = openai.Audio.transcribe(
            model="whisper-1", 
            file=audio_file
        )
        return response['text']
    except Exception as e:
        logging.error(f"Audio transcription failed: {e}")
        return "No se pudo procesar el mensaje de audio."


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
    message_type = message["type"]

    if message_type == "text":
        message_body = message["text"]["body"]
    elif message_type == "audio":
        media_id = message["audio"]["id"]
        audio_content = download_audio_file(media_id)
        if audio_content:
            message_body = transcribe_audio(audio_content)
        else:
            message_body = "No se pudo procesar el mensaje de audio."
    else:
        message_body = "Tipo de mensaje no soportado."

    # OpenAI Integration
    response = generate_response(message_body, wa_id, name)
    response = process_text_for_whatsapp(response)

    # Send the response message
    data = get_text_message_input(wa_id, response)
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
