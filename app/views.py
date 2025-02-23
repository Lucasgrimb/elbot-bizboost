import logging
import json
from .utils.whatsapp_utils import send_template_message
from flask import Blueprint, request, jsonify, current_app

from .decorators.security import signature_required
from .utils.whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)

webhook_blueprint = Blueprint("webhook", __name__)
send_template_blueprint = Blueprint("send_template", __name__)


from datetime import datetime, timezone
import json
from flask import request, jsonify
import logging

def handle_message():
    """
    Handle incoming webhook events from the WhatsApp API.

    This function processes incoming WhatsApp messages and other events,
    such as delivery statuses. If the event is a valid message, it gets
    processed. If the incoming payload is not a recognized WhatsApp event,
    an error is returned.

    Every message send will trigger 4 HTTP requests to your webhook: message, sent, delivered, read.

    Returns:
        response: A tuple containing a JSON response and an HTTP status code.
    """
    body = request.get_json()

    # Imprimir el JSON completo del cuerpo de la solicitud
    logging.info(f"Received payload: {json.dumps(body, indent=2)}")

    # Check if it's a WhatsApp status update
    if (
        body.get("entry", [{}])[0]
        .get("changes", [{}])[0]
        .get("value", {})
        .get("statuses")
    ):
        logging.info("Received a WhatsApp status update.")
        return jsonify({"status": "ok"}), 200

    try:
        # Verificar si el mensaje es válido y su timestamp
        if is_valid_whatsapp_message(body):
            message = body["entry"][0]["changes"][0]["value"]["messages"][0]
            timestamp = int(message.get("timestamp", 0))
            
            # Verificar si el mensaje se envió hace más de una hora
            if not is_recent_message(timestamp):
                logging.warning("Message timestamp exceeds one hour. Ignoring message.")
                return jsonify({"status": "ignored", "message": "Message too old."}), 200

            process_whatsapp_message(body)
            return jsonify({"status": "ok"}), 200
        else:
            # If the request is not a WhatsApp API event, return an error
            return (
                jsonify({"status": "error", "message": "Not a WhatsApp API event"}),
                404,
            )
    except json.JSONDecodeError:
        logging.error("Failed to decode JSON")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400

def is_recent_message(timestamp):
    """
    Check if the timestamp is within the last hour.

    Args:
        timestamp (int): The epoch time of the message.

    Returns:
        bool: True if the message is recent, False otherwise.
    """
    current_time = datetime.now(timezone.utc).timestamp()
    time_difference = current_time - timestamp

    # 3600 seconds = 1 hour
    return time_difference <= 3600




# Required webhook verification for WhatsApp
def verify():
    # Parse params from the webhook verification request
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    # Check if a token and mode were sent
    if mode and token:
        # Check the mode and token sent are correct
        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            # Respond with 200 OK and challenge token from the request
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            logging.info("VERIFICATION_FAILED")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    else:
        # Responds with '400 Bad Request' if verify tokens do not match
        logging.info("MISSING_PARAMETER")
        return jsonify({"status": "error", "message": "Missing parameters"}), 400


@webhook_blueprint.route("/webhooks", methods=["GET"])
def webhook_get():
    return verify()


@webhook_blueprint.route("/webhooks", methods=["POST"])
@signature_required
def webhook_post():
    return handle_message()


@send_template_blueprint.route("/send-messages", methods=["POST"])
def send_messages():
    """
    API endpoint to send template messages to a list of phone numbers.

    Expects a JSON payload with the following keys:
        - phones: List of phone numbers (e.g., [{"telefono": "+54 9 11 5723-0597"}, ...])

    Returns:
        JSON response indicating success or failure.
    """ 
    try:
        data = request.get_json()

        # Validar estructura del JSON
        phones = data.get("phones")
        template_name = "jelko_prueba_plantilla"  # Nombre de la plantilla

        components = None  # NO enviar componentes, ya que la plantilla no tiene placeholders

        if not phones or not template_name:
            return jsonify({"status": "error", "message": "Missing phones or template_name"}), 400

        # Extraer y limpiar números de teléfono
        recipients = [phone["telefono"].replace(" ", "").replace("-", "") for phone in phones if "telefono" in phone]

        if not recipients:
            return jsonify({"status": "error", "message": "No valid phone numbers provided"}), 400

        # Enviar mensajes a cada número
        for recipient in recipients:
            logging.info(f"Sending template message to {recipient}.")
            send_template_message(recipient, template_name, components=components)

        return jsonify({"status": "success", "message": f"Messages sent to {len(recipients)} recipients"}), 200

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

