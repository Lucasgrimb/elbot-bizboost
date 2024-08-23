import shelve
import os

# Opción A: Eliminar la base de datos de threads
if os.path.exists("threads_db.db"):
    os.remove("threads_db.db")
    print("Threads database file has been deleted.")

# Opción B: Limpiar la base de datos sin eliminar el archivo
with shelve.open("threads_db", writeback=True) as threads_shelf:
    threads_shelf.clear()
    print("All threads have been cleared.")
