
import shelve

def clear_all_histories():
    # Abre el archivo shelve que contiene los historiales de chat
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        # Elimina todos los historiales de chat
        threads_shelf.clear()
        print("All chat histories have been cleared.")

if __name__ == "__main__":
    confirmation = input("Are you sure you want to clear all chat histories? Type 'yes' to confirm: ")
    if confirmation.lower() == 'yes':
        clear_all_histories()
    else:
        print("Operation cancelled.")
