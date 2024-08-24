from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chat_models import ChatOpenAI
from langchain.memory import ChatMessageHistory
import os
import requests
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableBranch
from dotenv import load_dotenv
import logging
import shelve
from openai import OpenAI
from langchain.schema import Document
from datetime import datetime, timedelta
import json

# Set up OpenAI API key
def setup_openai_api():
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    print("OpenAI API Key configured.")

# Initialize chat model
def initialize_chat_model():
    print("Initializing Chat Model.")
    return ChatOpenAI(model="gpt-3.5-turbo-1106", temperature=0.2)

# Create chat history
# def create_chat_history():
#     print("Creating new chat history.")
#     return ChatMessageHistory()
def create_chat_history():
    print("Creating new chat history.")
    history = ChatMessageHistory()
    # Inicializa la historia del chat con un mensaje de saludo inicial o introducción al proyecto
    history.add_message("system", "¡Hola! Soy Agustín, estoy aquí para ayudarte con todo lo relacionado al proyecto Bizboost.")
    return history


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

# Process JSON data for RAG

def process_json_data(json_data):
    if json_data is None:
        print("No JSON data available to process.")
        return None

    print("Processing JSON Data")
    try:
        json_string = json.dumps(json_data, ensure_ascii=False)

        print("Splitting texts into smaller chunks.")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        all_splits = text_splitter.create_documents([json_string])

        print("Creating Embeddings and Vectorstore.")
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.from_documents(documents=all_splits, embedding=embeddings)
        retriever = vectorstore.as_retriever(k=5)  # Aumentar k para más precisión

        return retriever
    except Exception as e:
        print(f"Error processing JSON data: {e}")
        return None

# Create prompt template with sales focus
def create_prompt_template():
    print("Creating Prompt Template.")
    return ChatPromptTemplate.from_messages(
        [
            ("system", "Sos Agustín, experto en el proyecto Bizboost. Ayudás a las PYMES a entender cómo Bizboost puede mejorar su negocio a través de la automatización de la prospección de clientes y la gestión de interacciones. Usá lenguaje simple y accesible, pero sé persuasivo y motivador. Si no podés responder a una consulta, redirigí la conversación a la funcionalidad principal del proyecto:"),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
# Create retrieval chain
def create_retrieval_chain(chat, prompt):
    print("Creating Retrieval Chain.")
    try:
        # Mejor manejo de errores y asegurar que el prompt está bien formado
        return create_stuff_documents_chain(chat, prompt)
    except Exception as e:
        print(f"Error creating retrieval chain: {e}")
        return None

# Create query transformation chain
def create_query_transformation_chain(chat, retriever):
    print("Creating Query Transformation Chain.")
    query_transform_prompt = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="messages"),
            ("user", "Basado en la conversación anterior, genera una consulta precisa para recuperar la información más relevante sobre Bizboost."),
        ]
    )

    return RunnableBranch(
        (
            lambda x: len(x.get("messages", [])) == 1,
            (lambda x: x["messages"][-1].content) | retriever,
        ),
        query_transform_prompt | chat | StrOutputParser() | retriever,
    ).with_config(run_name="chat_retriever_chain")

# Create conversational retrieval chain
def create_conversational_retrieval_chain(retriever_chain, retrieval_chain):
    print("Creating Conversational Retrieval Chain.")
    return RunnablePassthrough.assign(
        context=retriever_chain,
    ).assign(
        answer=retrieval_chain,
    ).with_config(run_name="conversational_retrieval_chain")

# Local storage for chat threads using shelve
def check_if_thread_exists(wa_id):
    print(f"Checking if thread exists for wa_id: {wa_id}")
    with shelve.open("threads_db") as threads_shelf:
        chat_history = threads_shelf.get(wa_id, None)
        if isinstance(chat_history, ChatMessageHistory):
            print(f"Thread found for wa_id: {wa_id}")
            return chat_history
        else:
            print(f"No thread found for wa_id: {wa_id}")
            return None

def store_thread(wa_id, chat_history):
    print(f"Storing thread for wa_id: {wa_id}")
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        if isinstance(chat_history, ChatMessageHistory):
            threads_shelf[wa_id] = chat_history
        else:
            print("Error: Trying to store something that is not a ChatMessageHistory.")

# Main function to handle chat
def run_chat(wa_id, name):
    setup_openai_api()
    chat = initialize_chat_model()

    # Check if chat history exists for this wa_id
    chat_history = check_if_thread_exists(wa_id)
    if chat_history is None:
        chat_history = create_chat_history()
        store_thread(wa_id, chat_history)

    # Fetch and process JSON data
    url = "https://crescendoapi-pro.vercel.app/api/bizboost"
    json_data = fetch_json_data(url)
    retriever = process_json_data(json_data)

    if retriever is None:
        print("No data available to process.")
        return

    # Create the chains
    prompt = create_prompt_template()
    retrieval_chain = create_retrieval_chain(chat, prompt)
    query_transforming_retriever_chain = create_query_transformation_chain(chat, retriever)
    conversational_retrieval_chain = create_conversational_retrieval_chain(query_transforming_retriever_chain, retrieval_chain)

    # The first message always comes from the user, so we directly get it from the history
    user_input = chat_history.messages[-1].content
    print(f"User input: {user_input}")

    # Process the query and generate a response
    transformed_query = query_transforming_retriever_chain.invoke({
        "messages": chat_history.messages
    })

    # Access the content of documents if transformed_query is a list of Documents
    if isinstance(transformed_query, list) and isinstance(transformed_query[0], Document):
        transformed_query = " ".join([doc.page_content for doc in transformed_query])

    print(f"Transformed query: {transformed_query}")

    # Get relevant context
    retrieved_context = retriever.get_relevant_documents(transformed_query)
    concatenated_context = " ".join([doc.page_content for doc in retrieved_context])

    print(f"Retrieved context: {concatenated_context}")

    # Create final prompt and send it to OpenAI
    prompt_to_send = {
        "messages": chat_history.messages,
        "context": concatenated_context
    }

    print(f"Prompt being sent to OpenAI: {prompt_to_send}")

    # Generate the response using LangChain
    response = conversational_retrieval_chain.invoke(prompt_to_send)

    # Ensure the response is a string
    new_message = response.get('answer', '')
    if not isinstance(new_message, str):
        new_message = str(new_message)

    print(f"Generated response: {new_message}")

    # Add the generated message to the chat history
    chat_history.add_ai_message(new_message)

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
    chat_history.add_user_message(message_body)
    print(f"User message added to history: {message_body}")

    # Store updated chat history before running chat
    store_thread(wa_id, chat_history)

    # Run chat logic to get AI response
    new_message = run_chat(wa_id, name)

    return new_message