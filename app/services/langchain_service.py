import logging
import os
import requests
import json
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chat_models import ChatOpenAI
from langchain.memory import ChatMessageHistory
import redis
from langchain.schema import HumanMessage, AIMessage

# Set up Redis connection
redis_client = redis.Redis(
    host='redis-19468.c308.sa-east-1-1.ec2.redns.redis-cloud.com',  # Host de Redis
    port=19468,  # Puerto de Redis
    password='7a4cteGSD9iPbftOLGtoktsju5CoFGch',  # Contraseña de Redis
    db=0  # Base de datos Redis (por defecto 0)
)

# Set up OpenAI API key
def setup_openai_api():
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    print("OpenAI API Key configured.")

# Initialize chat model
def initialize_chat_model():
    print("Initializing Chat Model.")
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# Create chat history
def create_chat_history():
    print("Creating new chat history.")
    history = ChatMessageHistory()
    # Añadir el mensaje en el formato correcto utilizando HumanMessage
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
        else:
            chat_history.add_message(HumanMessage(role=msg["role"], content=msg["content"]))  # fallback para otros roles
    return chat_history

# Fetch JSON data from endpoint
def fetch_json_data(url):
    print(f"Fetching JSON data from {url}")
    try:
        response = requests.get(url, timeout=10)  # Añadir un timeout para evitar que se quede colgado
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
        # Función recursiva para extraer todos los valores del JSON como texto
        def extract_text_from_json(data):
            texts = []

            if isinstance(data, dict):
                for key, value in data.items():
                    texts.extend(extract_text_from_json(value))  # Recursividad para diccionarios
            elif isinstance(data, list):
                for item in data:
                    texts.extend(extract_text_from_json(item))  # Recursividad para listas
            else:
                if isinstance(data, str):  # Solo agregamos strings
                    print(f"Extracted text: {data}")  # Imprimir el valor extraído
                    texts.append(data)
                    
            return texts

        # Extraer todo el texto del JSON
        texts = extract_text_from_json(json_data)
        
        # Concatenar todos los textos en un solo string para usarlo como contexto
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
            ("system", "Sos Agustín, experto en el proyecto Bizboost. Ayudás a las PYMES a entender cómo Bizboost puede mejorar su negocio a través de la automatización de la prospección de clientes y la gestión de interacciones. Usá lenguaje simple y accesible, pero sé persuasivo y motivador. Si no podés responder a una consulta, redirigí la conversación a la funcionalidad principal del proyecto. Solo responder consultas con informacion presente en el contexto. No responder con textos demasiado largos. No responder consultas sobre cuestiones no relacionadas al proyecto. Aclará que solo hablás del proyecto."),
            ("system", f"Contexto:\n{context}"),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

# Check if chat thread exists in Redis
def check_if_thread_exists(wa_id):
    print(f"Checking if thread exists for wa_id: {wa_id}")
    serialized_data = redis_client.get(wa_id)
    if serialized_data is not None:
        print(f"Thread found for wa_id: {wa_id}")
        return deserialize_chat_history(serialized_data)
    else:
        print(f"No thread found for wa_id: {wa_id}")
        return None

# Store chat thread in Redis
def store_thread(wa_id, chat_history):
    print(f"Storing thread for wa_id: {wa_id}")
    serialized_data = serialize_chat_history(chat_history)
    redis_client.set(wa_id, serialized_data)

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
    recent_messages = chat_history.messages[-5:]  # Últimos 5 mensajes

    # Fetch and process JSON data
    url = "https://crescendoapi-pro.vercel.app/api/bizboost"
    json_data = fetch_json_data(url)
    context = process_json_data(json_data)

    if context is None:
        print("No context available to process.")
        return

    # Create the prompt with the full context
    prompt = create_prompt_template(context)
    
    # Construir la lista de mensajes para enviar al modelo
    prompt_messages = prompt.format_prompt(messages=recent_messages).to_messages()

    # Generate the response using the chat model
    response = chat(prompt_messages)

    # Ensure the response is a string
    new_message = response.content
    if not isinstance(new_message, str):
        new_message = str(new_message)

    print(f"Generated response: {new_message}")

    # Add the generated message to the chat history
    chat_history.add_message(AIMessage(role="assistant", content=new_message))

    # Store the updated chat history
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
