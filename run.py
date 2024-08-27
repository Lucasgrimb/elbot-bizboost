# import logging

# from app import create_app


# app = create_app()

# if __name__ == "__main__":
#     logging.info("Flask app started")
#     app.run(host="0.0.0.0", port=8000)

import logging
from app import create_app
from waitress import serve  # Importar waitress para usar como servidor WSGI

app = create_app()

if __name__ == "__main__":
    logging.info("Flask app started with Waitress")
    # Usar waitress en lugar de app.run()
    serve(app, host="0.0.0.0", port=8000)
