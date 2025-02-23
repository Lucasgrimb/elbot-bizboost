
import logging
from app import create_app
from waitress import serve  # Importar waitress para usar como servidor WSGI

app = create_app()

@app.route('/despertar', methods=['GET'])  # Ruta que responde a solicitudes GET
def despertar():
    return "Hola desde mi ruta GET"

@app.route("/")
def home():
    return "¡Hola, esta es la página principal de la aplicación!"

if __name__ == "__main__":
    logging.info("Flask app started with Waitress")
    # Usar waitress en lugar de app.run()
    serve(app, host="0.0.0.0", port=8000)


