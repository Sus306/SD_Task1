# insult_service_redis.py

import redis
import xmlrpc.server
import xmlrpc.client
import threading
import time
import random

# Conexión a Redis (localhost:6379, db 0)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
REDIS_INSULTS_KEY = 'insults'

# Lista local de suscriptores (almacena la URL de cada cliente suscriptor)
subscribers = []  # Ejemplo: "http://127.0.0.1:9000/RPC2"

def add_insult(insulto):
    """
    Agrega un nuevo insulto a Redis, solo si no existe.
    """
    added = r.sadd(REDIS_INSULTS_KEY, insulto)
    if added:
        print(f"Insulto agregado: {insulto}")
        return f"Insulto '{insulto}' agregado correctamente."
    else:
        return f"El insulto '{insulto}' ya existe."

def get_insults():
    """
    Devuelve la lista de insultos almacenados en Redis.
    """
    return list(r.smembers(REDIS_INSULTS_KEY))

def subscribe(client_ip, client_port):
    """
    Registra un cliente suscriptor, formando su URL a partir de IP y puerto.
    Se asume que el cliente expone un método XML-RPC 'recibir_insulto'.
    """
    url = f"http://{client_ip}:{client_port}/RPC2"
    if url not in subscribers:
        subscribers.append(url)
        print(f"Suscriptor agregado: {url}")
        return f"Suscriptor {url} agregado correctamente."
    else:
        return f"El suscriptor {url} ya estaba registrado."

def broadcast_insults():
    """
    Cada 5 segundos selecciona un insulto aleatorio de la lista y lo envía a todos los suscriptores.
    Si algún cliente no responde, se elimina de la lista.
    """
    while True:
        time.sleep(5)
        insults = get_insults()
        if insults and subscribers:
            insult = random.choice(insults)
            print(f"Difundiendo insulto: {insult}")
            active_subscribers = []
            for url in subscribers:
                try:
                    client = xmlrpc.client.ServerProxy(url, allow_none=True)
                    # Se llama a la función remota 'recibir_insulto'
                    client.recibir_insulto(insult)
                    active_subscribers.append(url)
                except Exception as e:
                    print(f"Error al enviar a {url}, removiendo: {e}")
            # Actualiza la lista de suscriptores activos
            subscribers[:] = active_subscribers

def start_service_server(port=8000):
    """
    Inicia el servidor XML-RPC del InsultService y el hilo del difusor.
    """
    server = xmlrpc.server.SimpleXMLRPCServer(("127.0.0.1", port), allow_none=True)
    server.register_function(add_insult, "add_insult")
    server.register_function(get_insults, "get_insults")
    server.register_function(subscribe, "subscribe")
    
    # Inicia el hilo que difunde insultos cada 5 segundos
    broadcaster = threading.Thread(target=broadcast_insults, daemon=True)
    broadcaster.start()
    
    print(f"InsultService en ejecución en el puerto {port}...")
    server.serve_forever()

if __name__ == "__main__":
    start_service_server()
