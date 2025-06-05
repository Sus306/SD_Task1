# Below is the updated `insult_service_xmlrpc.py` which uses a separate Redis logical database for each XML-RPC instance
# based on its port number (so port 8000 → db 0, 8001 → db 1, etc.).

import redis
import xmlrpc.server
import xmlrpc.client
import threading
import time
import random
import sys

# Constants
DEFAULT_XMLRPC_PORT = 8000
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_BASE_DB = 0  # db index for XML-RPC port DEFAULT_XMLRPC_PORT

# Placeholder for Redis connection:
r = None
REDIS_INSULTS_KEY = 'insults'

# List of subscriber URLs
subscribers = []

def add_insult(insulto):
    added = r.sadd(REDIS_INSULTS_KEY, insulto)
    if added:
        print(f"[{port}] Insulto agregado: {insulto}")
        return f"Insulto '{insulto}' agregado correctamente."
    else:
        return f"El insulto '{insulto}' ya existe."

def get_insults():
    return list(r.smembers(REDIS_INSULTS_KEY))

def subscribe(client_ip, client_port):
    url = f"http://{client_ip}:{client_port}/RPC2"
    if url not in subscribers:
        subscribers.append(url)
        print(f"[{port}] Suscriptor agregado: {url}")
        return f"Suscriptor {url} agregado correctamente."
    else:
        return f"El suscriptor {url} ya estaba registrado."

def broadcast_insults():
    while True:
        time.sleep(5)
        insults = get_insults()
        if insults and subscribers:
            insult = random.choice(insults)
            print(f"[{port}] Difundiendo insulto: {insult}")
            active = []
            for url in subscribers:
                try:
                    client = xmlrpc.client.ServerProxy(url, allow_none=True)
                    client.recibir_insulto(insult)
                    active.append(url)
                except Exception:
                    pass
            subscribers[:] = active

def start_service_server(port=DEFAULT_XMLRPC_PORT):
    server = xmlrpc.server.SimpleXMLRPCServer(("127.0.0.1", port), allow_none=True)
    server.register_function(add_insult, "add_insult")
    server.register_function(get_insults, "get_insults")
    server.register_function(subscribe, "subscribe")
    broadcaster = threading.Thread(target=broadcast_insults, daemon=True)
    broadcaster.start()
    print(f"InsultService XMLRPC en puerto {port}")
    server.serve_forever()

if __name__ == "__main__":
    # Determine port from args
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XMLRPC_PORT

    # Compute Redis DB index per port
    db_index = (port - DEFAULT_XMLRPC_PORT) + REDIS_BASE_DB
    # Initialize Redis connection for this instance
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=db_index, decode_responses=True)

    start_service_server(port)
