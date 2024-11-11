import logging
import psycopg2
from psycopg2.extras import Json  # Import for Json handling
from flask import Blueprint, request, jsonify, make_response  # Added make_response here
import json  # Import the json module
from app.services.langchain_service import generate_response

# URL for PostgreSQL connection (replace placeholders with your actual credentials)
DB_URL = "postgresql://bizboost_postgre_user:9O5NXmVfO6fTGuDIEOSTPprfAmrKIp85@dpg-csmo8m88fa8c73a9gtp0-a.ohio-postgres.render.com/bizboost_postgre"

# Create the blueprint for the web chat API
web_chat_blueprint = Blueprint("web_chat", __name__)

def get_db_connection():
    return psycopg2.connect(DB_URL)

@web_chat_blueprint.route("/history", methods=["GET"])
def get_chat_history():
    """
    Endpoint to retrieve the full chat history from the PostgreSQL database.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT history FROM chat_history WHERE wa_id = %s", ("web_user",))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result[0]:
            logging.info(f"Fetched raw history from DB: {result[0]}")
            chat_history = result[0]
            # If chat_history is a string, deserialize it
            if isinstance(chat_history, str):
                chat_history = json.loads(chat_history)
        else:
            logging.info("No history found for web_user, returning empty list.")
            chat_history = []

        # Prepare the response data
        response_data = {"status": "success", "history": chat_history}
        response_json = json.dumps(response_data, ensure_ascii=False)
        return make_response(response_json, 200, {'Content-Type': 'application/json; charset=utf-8'})

    except Exception as e:
        logging.error(f"Error in get_chat_history: {str(e)}")
        error_response = {"status": "error", "message": str(e)}
        response_json = json.dumps(error_response, ensure_ascii=False)
        return make_response(response_json, 500, {'Content-Type': 'application/json; charset=utf-8'})

@web_chat_blueprint.route("/message", methods=["POST"])
def send_message_to_chatbot():
    """
    Endpoint to send a new message to the chatbot and receive a response.
    """
    try:
        data = request.get_json()
        user_message = data.get("message")

        if not user_message:
            return jsonify({"status": "error", "message": "Message content is required"}), 400

        # Generate chatbot response
        response = generate_response(user_message, "web_user", "web_user")

        # Prepare the response data
        response_data = {"status": "success", "response": response}

        # Convert the response data to JSON, ensuring non-ASCII characters are preserved
        response_json = json.dumps(response_data, ensure_ascii=False)

        # Create a Flask response with the correct content type
        return make_response(response_json, 200, {'Content-Type': 'application/json; charset=utf-8'})

    except Exception as e:
        logging.error(f"Error in send_message_to_chatbot: {str(e)}")
        error_response = {"status": "error", "message": str(e)}
        response_json = json.dumps(error_response, ensure_ascii=False)
        return make_response(response_json, 500, {'Content-Type': 'application/json; charset=utf-8'})

@web_chat_blueprint.route("/clear-history", methods=["POST"])
def clear_chat_history():
    """
    Endpoint to clear the chat history for 'web_user' in the database.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE wa_id = %s", ("web_user",))
        conn.commit()
        cursor.close()
        conn.close()
        logging.info("Cleared history for web_user.")

        # Prepare the response data
        response_data = {"status": "success", "message": "History cleared for web_user"}
        response_json = json.dumps(response_data, ensure_ascii=False)
        return make_response(response_json, 200, {'Content-Type': 'application/json; charset=utf-8'})

    except Exception as e:
        logging.error(f"Error clearing chat history: {str(e)}")
        error_response = {"status": "error", "message": str(e)}
        response_json = json.dumps(error_response, ensure_ascii=False)
        return make_response(response_json, 500, {'Content-Type': 'application/json; charset=utf-8'})
