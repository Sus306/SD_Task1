import redis
import xmlrpc.server
import socketserver
import threading
import logging
import time
import re
from xmlrpc.server import SimpleXMLRPCRequestHandler

logging.getLogger("xmlrpc.server").setLevel(logging.CRITICAL)
# Conexión a Redis (localhost:6379, db 0)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
REDIS_INSULTS_KEY = 'insults'

# Cache local de insultos y lista de frases filtradas
insults_cache = []
filtered_texts = []

def update_insults_cache():
    global insults_cache
    while True:
        insults_cache = list(r.smembers(REDIS_INSULTS_KEY))
        time.sleep(10)

# Simplemente heredamos el handler, sin usarlo como decorator
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)
    # anula todos los mensajes de petición
    def log_request(self, code='-', size='-'):
        pass
    def log_message(self, format, *args):
        pass

def filter_phrase(phrase):
    """
    Recibe una frase y reemplaza cualquier palabra que coincida con un insulto
    (fetched fresh from Redis) por "***", guarda el resultado.
    """
    # Always fetch the latest insult set
    current_insults = list(r.smembers(REDIS_INSULTS_KEY))
    filtered = phrase
    for insult in current_insults:
        filtered = re.sub(r'\b' + re.escape(insult) + r'\b', "***", filtered, flags=re.IGNORECASE)
    filtered_texts.append(filtered)
    return filtered

def get_filtered_texts():
    """
    Devuelve todas las frases que han sido filtradas hasta el momento.
    """
    return filtered_texts

def start_filter_server(port=8001):
    """
    Inicia el servidor XML-RPC del InsultFilter y el hilo de actualización de cache.
    """
    # Lanza el hilo de actualización de insultos
    updater = threading.Thread(target=update_insults_cache, daemon=True)
    updater.start()
    socketserver.TCPServer.allow_reuse_address = True
    
    # Configura y arranca el servidor XML-RPC usando nuestro RequestHandler
    server = xmlrpc.server.SimpleXMLRPCServer(
        ("127.0.0.1", port),
        requestHandler=RequestHandler,
        allow_none=True,
        logRequests=False
    )
    server.register_function(filter_phrase, "filter_phrase")
    server.register_function(get_filtered_texts, "get_filtered_texts")
    print(f"InsultFilter en ejecución en el puerto {port}...")
    server.serve_forever()

if __name__ == "__main__":
    start_filter_server()
