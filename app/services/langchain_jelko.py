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
# DB_URL = "postgresql://jelko_user:7JBd8Ni7HYAgIhuIY6F1CKWkCieZNDj5@dpg-ctn23opopnds73fjj1ig-a.ohio-postgres.render.com/jelko"
DB_URL = "postgresql://postgres:fZuhFgnXiYzTHeTZwOahogIWXcaRFLqR@postgres.railway.internal:5432/railway"

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
    history.add_message(HumanMessage(role="system", content="¡Hola! Soy Agustín, estoy aquí para ayudarte con todo lo relacionado a Jelko y sus productos."))
    return history

# Serialize chat history to JSON
def serialize_chat_history(chat_history):
    return json.dumps([{"role": m.role, "content": m.content} for m in chat_history.messages])

# Deserialize chat history from JSON
def deserialize_chat_history(serialized_data):
    if isinstance(serialized_data, list):
        print("Data is already a list, skipping JSON deserialization.")
        messages = serialized_data  # Si ya es lista, úsala directamente
    elif isinstance(serialized_data, str):
        print("Deserializing JSON string into list.")
        messages = json.loads(serialized_data)  # Deserializar si es un JSON string
    else:
        raise ValueError("Invalid data type for serialized_data")
    
    chat_history = ChatMessageHistory()
    for msg in messages:
        if msg["role"] == "user":
            chat_history.add_message(HumanMessage(role=msg["role"], content=msg["content"]))
        elif msg["role"] == "assistant":
            chat_history.add_message(AIMessage(role=msg["role"], content=msg["content"]))
    return chat_history

# Fetch JSON data from endpoint
# Fetch JSON data from a local file
def fetch_json_data_from_file(file_path):
    """
    Fetch JSON data from a local file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        dict: Parsed JSON data.
    """
    print(f"Fetching JSON data from file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        print("Data fetched successfully from file.")
        return data
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file {file_path}: {e}")
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
                    # Agregamos la clave para dar contexto (opcional)
                    texts.append(str(key))
                    texts.extend(extract_text_from_json(value))
            elif isinstance(data, list):
                for item in data:
                    texts.extend(extract_text_from_json(item))
            else:
                # Convertir cualquier otro tipo (int, float, bool, etc.) a string e incluirlo
                text = str(data)
                if text.strip():
                    print(f"Extracted text: {text}")
                    texts.append(text)
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
    return ChatPromptTemplate.from_messages([
        (
            "system",
            """Sos Agustín, un agente de ventas amigable y accesible de la marca Jelko, especializada en productos de embalaje. Tu objetivo es entablar una conversación cálida y personalizada con los clientes, informándoles sobre la empresa, sus productos y servicios, y persuadiéndolos a considerar a Jelko como su proveedor. Respondés de manera clara, breve y cálida, utilizando un tono humano y amigable. Hablá como si fueras un humano en criollo. Primero buscás generar conexión preguntando el nombre del cliente y conociendo brevemente su negocio o actividad. Tu enfoque inicial es conversar para descubrir sus necesidades actuales relacionadas con productos de embalaje, identificando si es usuario directo (locales de ropa, telas, comercios) o revendedor (papelerías, mayoristas). Podés preguntar: *"¿Hoy en día usan cinta de embalar? En Jelko somos importadores directos"*, *"¿Qué tipo de embalaje usan más seguido?"*, *"¿Trabajan como revendedores o usan los productos directamente?"*, *"¿En qué rubro están? ¿Ropa, telas, comercio, o algo distinto?"*, *"¿Les interesa mejorar calidad o costos del embalaje? Tenemos precios competitivos, sobre todo por mayor"*. Si el cliente intenta pelear el precio, decí que no estás autorizado para negociar y redirigí inmediatamente a Felipe. Adaptá la conversación según sus respuestas: para clientes directos, destacá calidad y pegamento de las cintas; para revendedores, precios mayoristas y relaciones duraderas. **No hagás recomendaciones de productos**; el cliente ya sabe lo que necesita, **excepto que te pida una recomendación**. Cuando un cliente pregunte por el precio total, asegurate de hacer el cálculo correcto, Total = (precio unitario) * (cantidad de unidades por caja) * (cantidad de cajas). Para esto, usa la siguiente fórmula:  **No des precios sin antes preguntar la cantidad requerida** (ej: *"¿Cuantas cajas necesitabas?"*), Solo redirigí al contacto principal, Felipe Garfunkel (+5491125069266), cuando haya interés claro en compra, pero **antes pedí confirmación explícita** (ej: *"¿Podés confirmar que querés avanzar? Así te contacto con Felipe, quien te va a asesorar con el envío, pago y detalles finales"*). No cerrés ventas directamente, pero resaltá las ventajas de Jelko (calidad, atención personalizada, experiencia) para motivar al cliente a dar el próximo paso. Si no podés responder algo, explicalo con amabilidad y ofrecé conectar con Felipe solo si es necesario. Al redirigir, transmití que el siguiente paso es concretar la venta, enviar el pedido directo, *el cliente le envía a Felipe “ hola, quiero 10 cajas de cinta”*. Usá frases entusiastas como *"¡Buenísimo! Para armar tu pedido, escribile a Felipe la cantidad que necesitabas y tu dirección. +541166129990. Él se encarga de todo: asesoría, envío y pago"*. Evitá emojis repetitivos, chistes y lenguaje formal. Mantené el foco en generar confianza y guiar al cliente hacia Felipe cuando esté listo para acciones concretas."""
        ),
        ("system", f"Contexto:\n{context}"),
        MessagesPlaceholder(variable_name="messages"),
    ])


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
        serialized_data = result[0]
        print(f"Serialized data from DB: {serialized_data}, Type: {type(serialized_data)}")
        return deserialize_chat_history(serialized_data)
    else:
        print(f"No thread found for wa_id: {wa_id}")
        return None

# Store chat thread in PostgreSQL
def store_thread(wa_id, chat_history):
    print(f"Storing thread for wa_id: {wa_id}")
    serialized_data = serialize_chat_history(chat_history)  # JSON serializado
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO chat_history (wa_id, history)
        VALUES (%s, %s)
        ON CONFLICT (wa_id) DO UPDATE SET history = EXCLUDED.history
        """,
        (wa_id, serialized_data),
    )
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
    
    # Ruta al archivo JSON local
    json_file_path = os.path.join("app", "contexts", "jelko.json")
    
    # Fetch and process JSON data
    json_data = fetch_json_data_from_file(json_file_path)
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
