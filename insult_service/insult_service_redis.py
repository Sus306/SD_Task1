# insult_service_redis_pubsub.py
import redis
import threading
import time
import random

# Conexión a Redis (ajusta la IP/puerto si es necesario)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Llave para almacenar los insultos (set para evitar duplicados)
INSULTS_KEY = "insults"
# Canal para publicar los insultos
BROADCAST_CHANNEL = "insults_channel"

def add_insult(insulto):
    """
    Agrega un insulto a Redis, solo si no existe.
    """
    result = r.sadd(INSULTS_KEY, insulto)
    if result:
        print(f"Insulto agregado: {insulto}")
        return f"Insulto '{insulto}' agregado correctamente."
    else:
        return f"El insulto '{insulto}' ya existe."

def get_insults():
    """
    Devuelve la lista de insultos almacenados.
    """
    return list(r.smembers(INSULTS_KEY))

def broadcast_insults():
    """
    Cada 5 segundos, selecciona un insulto aleatorio del conjunto y lo publica en el canal.
    """
    while True:
        time.sleep(5)
        insults = get_insults()
        if insults:
            insult = random.choice(insults)
            print(f"Publicando insulto: {insult}")
            r.publish(BROADCAST_CHANNEL, insult)

def start_insult_service():
    """
    Inicia el servicio:
      - Se pueden agregar insultos mediante add_insult (por ejemplo, vía algún mecanismo remoto).
      - Inicia el hilo que difunde insultos en el canal.
    """
    threading.Thread(target=broadcast_insults, daemon=True).start()
    print("InsultService (Redis Pub/Sub) en ejecución...")
    # Aquí se podría esperar solicitudes remotas o simplemente mantener el servicio activo.
    while True:
        time.sleep(1)

if __name__ == "__main__":
    start_insult_service()
