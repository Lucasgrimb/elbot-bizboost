import shelve
import sys
from langchain.memory import ChatMessageHistory
from langchain.schema import HumanMessage, AIMessage

# Función para ver el historial de conversaciones
def view_chat_history(wa_id):
    with shelve.open("threads_db") as threads_shelf:
        chat_history = threads_shelf.get(wa_id, None)
        if chat_history is None:
            print(f"No se encontró historial para el wa_id: {wa_id}")
        elif isinstance(chat_history, ChatMessageHistory):
            print(f"Historial de conversación para {wa_id}:")
            for message in chat_history.messages:
                if isinstance(message, HumanMessage):
                    role = "Usuario"
                elif isinstance(message, AIMessage):
                    role = "Asistente"
                else:
                    role = "Desconocido"
                print(f"{role}: {message.content}")
        else:
            print(f"El historial recuperado no es de tipo ChatMessageHistory para wa_id: {wa_id}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python view_chat_history.py <wa_id>")
    else:
        wa_id = sys.argv[1]
        view_chat_history(wa_id)
