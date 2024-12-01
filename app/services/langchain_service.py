import logging
import os
import requests
import json
import psycopg2
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chat_models import ChatOpenAI
from langchain.memory import ChatMessageHistory
from langchain.schema import HumanMessage, AIMessage

# URL de conexión a PostgreSQL
DB_URL = "postgresql://bizboost_postgre_user:9O5NXmVfO6fTGuDIEOSTPprfAmrKIp85@dpg-csmo8m88fa8c73a9gtp0-a.ohio-postgres.render.com/bizboost_postgre"

# Función para conectar a PostgreSQL
def get_db_connection():
    return psycopg2.connect(DB_URL)

# Set up OpenAI API key
def setup_openai_api():
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    print("OpenAI API Key configured.")

# Initialize chat model
def initialize_chat_model():
    print("Initializing Chat Model.")
    return ChatOpenAI(model="gpt-4o", temperature=0.2)

# Create chat history
def create_chat_history():
    print("Creating new chat history.")
    history = ChatMessageHistory()
    history.add_message(HumanMessage(role="system", content="¡Hola! Soy Agustín, estoy aquí para ayudarte con todo lo relacionado al proyecto Bizboost."))
    return history

# Serialize chat history to JSON
def serialize_chat_history(chat_history):
    return json.dumps([{"role": m.role, "content": m.content} for m in chat_history.messages])

# Deserialize chat history from JSON
def deserialize_chat_history(serialized_data):
    chat_history = ChatMessageHistory()
    messages = json.loads(serialized_data)
    for msg in messages:
        if msg["role"] == "user":
            chat_history.add_message(HumanMessage(role=msg["role"], content=msg["content"]))
        elif msg["role"] == "assistant":
            chat_history.add_message(AIMessage(role=msg["role"], content=msg["content"]))
    return chat_history

# Fetch JSON data from endpoint
def fetch_json_data(url):
    print(f"Fetching JSON data from {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print("Data fetched successfully.")
        data = response.json()
        if not data:
            raise ValueError("No JSON data found at the endpoint.")
        return data
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    except ValueError as ve:
        print(f"Data error: {ve}")
        return None

# Process JSON data
def process_json_data(json_data):
    if json_data is None:
        print("No JSON data available to process.")
        return None

    print("Processing JSON Data")
    try:
        def extract_text_from_json(data):
            texts = []
            if isinstance(data, dict):
                for key, value in data.items():
                    texts.extend(extract_text_from_json(value))
            elif isinstance(data, list):
                for item in data:
                    texts.extend(extract_text_from_json(item))
            else:
                if isinstance(data, str):
                    print(f"Extracted text: {data}")
                    texts.append(data)
            return texts

        texts = extract_text_from_json(json_data)
        concatenated_text = "\n".join([text for text in texts if text.strip()])

        if not concatenated_text:
            print("No valid text data found in the JSON.")
            return None

        print(f"Context size: {len(concatenated_text)} characters")
        return concatenated_text
    except Exception as e:
        print(f"Error processing JSON data: {e}")
        return None

# Create prompt template with sales focus
def create_prompt_template(context):
    print("Creating Prompt Template.")
    return ChatPromptTemplate.from_messages(
        [
            ("system", "Sos Agustín, un agente de ventas experto en el proyecto Bizboost. Tu misión es ayudar a las PYMEs a entender cómo Bizboost puede transformar su negocio a través de la automatización de la prospección de clientes y la gestión de interacciones. Tus respuestas deben ser breves, directas y enfocarse en un solo beneficio o característica por vez, para mantener la atención del cliente. Si el cliente quiere más detalles, invitá a seguir la conversación haciendo preguntas que mantengan su interés. Adaptá el tono al cliente, siempre de manera profesional, motivadora y cercana.Respondé siempre en menos de **3 oraciones**. Si no sabés algo, redirigí la conversación a las ventajas principales de Bizboost. Hablá solo del proyecto y sus funcionalidades, no abordes temas externos. Actuá como un experto apasionado por la tecnología y comprometido con el éxito de las PYMEs. En caso de que te pidan el contacto de algun representante de la empresa, deciles que se pueden comunicar con uno de los desarrolladores, Lucas Grimberg escribiendo al numero 1164903955. Aparte de español podes hablar en ingles y frances"),
            ("system", f"Contexto:\n{context}"),
            MessagesPlaceholder(variable_name="messages"),

        ]
    )

# Check if chat thread exists in PostgreSQL
def check_if_thread_exists(wa_id):
    print(f"Checking if thread exists for wa_id: {wa_id}")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT history FROM chat_history WHERE wa_id = %s", (wa_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if result:
        print(f"Thread found for wa_id: {wa_id}")
        serialized_data = result[0]
        return deserialize_chat_history(serialized_data)
    else:
        print(f"No thread found for wa_id: {wa_id}")
        return None

# Store chat thread in PostgreSQL
def store_thread(wa_id, chat_history):
    print(f"Storing thread for wa_id: {wa_id}")
    serialized_data = serialize_chat_history(chat_history)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chat_history (wa_id, history)
        VALUES (%s, %s)
        ON CONFLICT (wa_id) DO UPDATE SET history = EXCLUDED.history
    """, (wa_id, json.dumps(serialized_data)))
    conn.commit()
    cursor.close()
    conn.close()

# Main function to handle chat
def run_chat(wa_id, name):
    setup_openai_api()
    chat = initialize_chat_model()

    # Check if chat history exists for this wa_id
    chat_history = check_if_thread_exists(wa_id)
    if chat_history is None:
        chat_history = create_chat_history()
        store_thread(wa_id, chat_history)

    # Limitar el historial de chat a los últimos 5 mensajes relevantes
    recent_messages = chat_history.messages[-5:] 
    print(recent_messages)
    
    # Fetch and process JSON data
    url = "https://crescendoapi-pro.vercel.app/api/bizboost"
    json_data = fetch_json_data(url)
    context = process_json_data(json_data)

    if context is None:
        print("No context available to process.")
        return

    # Create the prompt with the full context
    prompt = create_prompt_template(context)
    prompt_messages = prompt.format_prompt(messages=recent_messages).to_messages()

    # Generate the response using the chat model
    response = chat(prompt_messages)
    new_message = response.content if isinstance(response.content, str) else str(response.content)
    print(f"Generated response: {new_message}")

    # Add the generated message to the chat history
    chat_history.add_message(AIMessage(role="assistant", content=new_message))
    store_thread(wa_id, chat_history)

    return new_message

# Main function to generate response
def generate_response(message_body, wa_id, name):
    print(f"Generating response for wa_id {wa_id} with message body: {message_body}")
    
    if not isinstance(message_body, str):
        message_body = str(message_body)

    # Fetch existing chat history or create new one
    chat_history = check_if_thread_exists(wa_id)
    if chat_history is None:
        logging.info(f"Creating new thread for {name} with wa_id {wa_id}")
        chat_history = create_chat_history()
    else:
        logging.info(f"Retrieving existing thread for {name} with wa_id {wa_id}")

    # Add user message to chat history
    chat_history.add_message(HumanMessage(role="user", content=message_body))
    print(f"User message added to history: {message_body}")

    # Store updated chat history before running chat
    store_thread(wa_id, chat_history)

    # Run chat logic to get AI response
    new_message = run_chat(wa_id, name)
    return new_message