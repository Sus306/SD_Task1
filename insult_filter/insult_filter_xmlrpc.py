#!/usr/bin/env python3
import sys
import logging
import threading
import socketserver
import time
import re
import redis
import xmlrpc.server
from xmlrpc.server import SimpleXMLRPCRequestHandler

logging.getLogger("xmlrpc.server").setLevel(logging.CRITICAL)

# — Parámetros dinámicos según puerto —
# Puerto por defecto
DEFAULT_PORT = 8001
# Base para calcular el índice de BD
BASE_PORT = 8001

# Parsear puerto de los args
port = DEFAULT_PORT
if len(sys.argv) > 1:
    try:
        port = int(sys.argv[1])
    except ValueError:
        print(f"Puerto inválido: {sys.argv[1]}")
        sys.exit(1)

# Calcular índice de Redis DB: 0 para 8001, 1 para 8002, etc.
db_index = max(0, port - BASE_PORT)

# Conexión a Redis en la BD correspondiente
r = redis.Redis(host='localhost', port=6379, db=db_index, decode_responses=True)
REDIS_INSULTS_KEY = 'insults'

# Cache local de insultos y lista de frases filtradas
insults_cache = []
filtered_texts = []

def update_insults_cache():
    global insults_cache
    while True:
        try:
            insults_cache = list(r.smembers(REDIS_INSULTS_KEY))
        except Exception:
            pass
        time.sleep(10)

class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)
    def log_request(self, code='-', size='-'): pass
    def log_message(self, format, *args): pass

def filter_phrase(phrase):
    """
    Reemplaza cualquier insulto por "***" (usa datos frescos de Redis).
    """
    # Recogemos frescos los insultos de Redis
    current_insults = list(r.smembers(REDIS_INSULTS_KEY))
    filtered = phrase
    for insult in current_insults:
        filtered = re.sub(r'\b' + re.escape(insult) + r'\b', "***", filtered, flags=re.IGNORECASE)
    filtered_texts.append(filtered)
    return filtered

def get_filtered_texts():
    """
    Devuelve el histórico de frases filtradas.
    """
    return filtered_texts

def start_filter_server(port):
    # Arranca el hilo de refresco de cache
    threading.Thread(target=update_insults_cache, daemon=True).start()
    socketserver.TCPServer.allow_reuse_address = True

    server = xmlrpc.server.SimpleXMLRPCServer(
        ("127.0.0.1", port),
        requestHandler=RequestHandler,
        allow_none=True,
        logRequests=False
    )
    server.register_function(filter_phrase, "filter_phrase")
    server.register_function(get_filtered_texts, "get_filtered_texts")
    print(f"[Port {port} | Redis DB {db_index}] InsultFilter XML-RPC arrancado")
    server.serve_forever()

if __name__ == "__main__":
    start_filter_server(port)
