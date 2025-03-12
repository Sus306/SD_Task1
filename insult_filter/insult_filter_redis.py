# insult_filter_redis_workqueue.py
import redis
import time
import re

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Llave para la cola de textos a filtrar y para la lista de resultados filtrados
TEXTS_QUEUE = "texts_queue"
RESULTS_LIST = "filtered_texts"

# Lista local de insultos a censurar (puedes ampliarla o almacenarla también en Redis)
INSULTS = ["idiota", "estúpido", "imbécil", "tonto"]

def filter_text(text):
    """
    Reemplaza en el texto todas las ocurrencias de insultos por "CENSORED".
    """
    filtered = text
    for insult in INSULTS:
        filtered = re.sub(r'\b' + re.escape(insult) + r'\b', "CENSORED", filtered, flags=re.IGNORECASE)
    return filtered

def process_texts():
    """
    Consume textos de la cola, los filtra y almacena el resultado.
    """
    while True:
        # BLPOP bloquea hasta obtener un mensaje de la cola
        item = r.blpop(TEXTS_QUEUE, timeout=0)
        if item:
            # item es una tupla (queue_name, mensaje)
            original_text = item[1]
            filtered_text = filter_text(original_text)
            r.rpush(RESULTS_LIST, filtered_text)
            print(f"Procesado: '{original_text}' -> '{filtered_text}'")

def start_filter_service():
    print("InsultFilter (Redis Work Queue) en ejecución...")
    process_texts()

if __name__ == "__main__":
    start_filter_service()
