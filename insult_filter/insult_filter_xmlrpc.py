# insult_filter_redis.py

import redis
import xmlrpc.server
import threading
import time
import re

# Conexión a Redis (localhost:6379, db 0)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
REDIS_INSULTS_KEY = 'insults'

# Cache local de insultos, para evitar consultar Redis en cada filtrado
insults_cache = []

def update_insults_cache():
    """
    Actualiza la cache local de insultos cada 10 segundos.
    """
    global insults_cache
    while True:
        try:
            insults_cache = list(r.smembers(REDIS_INSULTS_KEY))
            print("Cache de insultos actualizada:", insults_cache)
        except Exception as e:
            print("Error actualizando cache de insultos:", e)
        time.sleep(10)

def filter_phrase(phrase):
    """
    Recibe una frase, y reemplaza cualquier palabra que coincida con un insulto (de la cache) por "CENSORED".
    """
    filtered_phrase = phrase
    for insult in insults_cache:
        filtered_phrase = re.sub(r'\b' + re.escape(insult) + r'\b', "CENSORED", filtered_phrase, flags=re.IGNORECASE)
    return filtered_phrase

def start_filter_server(port=8001):
    """
    Inicia el servidor XML-RPC del InsultFilter y el hilo de actualización de cache.
    """
    thread = threading.Thread(target=update_insults_cache, daemon=True)
    thread.start()
    
    server = xmlrpc.server.SimpleXMLRPCServer(("127.0.0.1", port), allow_none=True)
    server.register_function(filter_phrase, "filter_phrase")
    print(f"InsultFilter en ejecución en el puerto {port}...")
    server.serve_forever()

if __name__ == "__main__":
    start_filter_server()
