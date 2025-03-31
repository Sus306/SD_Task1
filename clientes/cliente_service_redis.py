import redis
import threading

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def recibir_insultos():
    pubsub = r.pubsub()
    pubsub.subscribe("insults_channel")
    print("Escuchando insults_channel...")
    for message in pubsub.listen():
        if message["type"] == "message":
            print(f"Insulto recibido: {message['data']}")

def main():
    threading.Thread(target=recibir_insultos, daemon=True).start()

    print("Cliente listo para enviar insults al servicio.")
    while True:
        insulto = input("Introduce insulto para enviar al service (o 'salir'): ")
        if insulto.lower() == "salir":
            break
        r.sadd("insults", insulto)
        print(f"Enviado insulto '{insulto}' al service.")

if __name__ == "__main__":
    main()
