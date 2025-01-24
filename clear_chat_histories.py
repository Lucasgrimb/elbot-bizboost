import psycopg2
from psycopg2.extras import execute_values

# URL de conexión a PostgreSQL
DB_URL = "postgresql://jelko_user:7JBd8Ni7HYAgIhuIY6F1CKWkCieZNDj5@dpg-ctn23opopnds73fjj1ig-a.ohio-postgres.render.com/jelko"

def clear_postgresql_histories():
    try:
        # Conéctate a la base de datos
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()

        # Ejecuta la instrucción para eliminar todos los historiales
        cursor.execute("DELETE FROM chat_history")

        # Confirma los cambios
        conn.commit()
        print("All chat histories have been cleared from PostgreSQL.")

    except Exception as e:
        print(f"Error clearing chat histories: {e}")
    finally:
        # Cierra la conexión
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    confirmation = input("Are you sure you want to clear all chat histories from PostgreSQL? Type 'yes' to confirm: ")
    if confirmation.lower() == 'yes':
        clear_postgresql_histories()
    else:
        print("Operation cancelled.")
