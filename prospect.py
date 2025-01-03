import os
import json
import serpapi
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

# Cargar las variables de entorno desde .env
load_dotenv()

def setup_chat_model():
    """
    Inicializa el modelo de chat usando LangChain con OpenAI.
    """
    return ChatOpenAI(
        model="gpt-4",  # Cambia a "gpt-4" si tienes acceso
        temperature=0.7,  # Controla la creatividad de las respuestas
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )

def interpretar_json(chat_model, json_data):
    """
    Usa LangChain para interpretar el JSON y generar términos de búsqueda específicos.

    Parámetros:
        chat_model (ChatOpenAI): Instancia del modelo de chat.
        json_data (dict): Datos del JSON cargado.

    Retorna:
        list: Lista de términos de búsqueda generados por el modelo.
    """
    try:
        # Convertir JSON a texto
        json_text = json.dumps(json_data, ensure_ascii=False, indent=2)

        # Crear los mensajes
        messages = [
            SystemMessage(content="Eres un asistente experto en generación de leads. Genera términos concretos para buscar en Google Maps negocios b2b en Buenos Aires que podrían ser potenciales clientes del proyecto."),
            HumanMessage(content=f"Analiza el siguiente JSON y genera una lista con al menos 10 términos claros para buscar en Google Maps. JSON: {json_text}")
        ]

        # Generar respuesta usando el modelo
        response = chat_model.invoke(messages)

        # Imprimir la respuesta bruta para depuración
        #print("Respuesta bruta del modelo:", response.content)

        # Procesar la respuesta para limpiar los términos
        raw_terms = response.content.split("\n")  # Dividir por saltos de línea
        cleaned_terms = []

        for term in raw_terms:
            # Eliminar enumeración y comillas
            if ". " in term:  # Solo procesar si tiene un número enumerado
                cleaned_term = term.split(". ", 1)[1].strip('"').strip()
                cleaned_terms.append(cleaned_term)

        # Imprimir términos limpios para depuración
        print("Términos limpios:", cleaned_terms)

        # Retornar la lista de términos limpios
        return cleaned_terms

    except Exception as e:
        print(f"Error al interpretar el JSON con el modelo: {e}")
        return []

def search_google_maps(term, location="Buenos Aires"):
    """Realiza una búsqueda en Google Maps usando SerpApi."""
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise ValueError("La API key de SerpApi no está configurada.")
    
    # Crear cliente de SerpApi
    client = serpapi.Client(api_key=api_key)

    # Configurar los parámetros de búsqueda
    params = {
        "engine": "google_maps",
        "q": term,
        "location": location,
        "type": "search",
        "hl": "es",
    }

    # Realizar la búsqueda
    try:
        results = client.search(**params)
    except Exception as e:
        print(f"Error al realizar la búsqueda: {e}")
        return []

    businesses = []
    for result in results.get("local_results", []):
        business = {
            "name": result.get("title"),
            "phone": result.get("phone"),
            "coordinates": result.get("gps_coordinates", {})
        }
        if business["name"] and business["phone"]:
            businesses.append(business)
    
    return businesses

def main():
    # Cargar el archivo JSON de entrada
    try:
        with open("bizboost.json", "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except Exception as e:
        print(f"Error al cargar el JSON: {e}")
        return

    # Configurar el modelo de chat
    chat_model = setup_chat_model()

    # Generar términos de búsqueda usando el modelo
    #print("Generando términos de búsqueda...")
    search_terms = interpretar_json(chat_model, json_data)

    # Consolidar todos los resultados en un solo JSON
    all_results = {}

    for term in search_terms:
        #print(f"\nBuscando: {term} en Google Maps...")
        results = search_google_maps(term)
        all_results[term] = results

        if results:
            #print(f"Resultados encontrados para '{term}':")
            for business in results:
                coords = business.get("coordinates", {})
                print(f"- Nombre: {business['name']}, Teléfono: {business['phone']}, Coordenadas: {coords}")
        else:
            print(f"No se encontraron resultados para '{term}'.")

    # Mostrar el JSON consolidado con los resultados
    print("\nJSON consolidado con todos los resultados:")
    print(json.dumps(all_results, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()

