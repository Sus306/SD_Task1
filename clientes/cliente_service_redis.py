# client_insult_subscriber_redis.py
import redis
import threading

def listen_for_insults():
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    pubsub = r.pubsub()
    pubsub.subscribe("insults_channel")
    print("Cliente suscriptor: Escuchando en el canal 'insults_channel'...")
    for message in pubsub.listen():
        if message["type"] == "message":
            print("Insulto recibido:", message["data"])

if __name__ == "__main__":
    threading.Thread(target=listen_for_insults, daemon=True).start()
    input("Presiona Enter para salir...\n")
