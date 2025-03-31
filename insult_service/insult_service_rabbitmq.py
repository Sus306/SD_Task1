import pika
import threading
import time
import random
import json

# Conjunto para almacenar insultos (sin duplicados)
insults = {"idiota", "imbécil", "tonto", "estúpido"}  # Insults inicials

# Configuració de RabbitMQ
BROADCAST_EXCHANGE = "insult_broadcast"
RPC_QUEUE = "insult_rpc_queue"
params = pika.ConnectionParameters('localhost')

def add_insult(insult):
    """ Agrega un insulto si no existe. """
    if insult not in insults:
        insults.add(insult)
        print(f"Insult added: {insult}")
        return f"Insult '{insult}' added successfully."
    else:
        return f"Insult '{insult}' already exists."

def get_insults():
    """ Retorna la llista d'insults. """
    return list(insults)

def on_rpc_request(ch, method, props, body):
    """ Gestiona les sol·licituds RPC (afegir i obtenir insults). """
    try:
        request = json.loads(body)
        print(f"Received RPC request: {request}")  # Debugging
        command = request.get("command")
        response = None

        if command == "add_insult":
            response = add_insult(request.get("data"))
        elif command == "get_insults":
            response = get_insults()
        else:
            response = "Unknown command"

        print(f"Responding with: {response}")  # Debugging
        ch.basic_publish(
            exchange="",
            routing_key=props.reply_to,
            properties=pika.BasicProperties(correlation_id=props.correlation_id),
            body=json.dumps(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing RPC request: {e}")

def start_rpc_server():
    """ Inicia el servidor RPC en la cua insult_rpc_queue. """
    connection = pika.BlockingConnection(params)
    channel = connection.channel()

    # Creació de la cua RPC
    channel.queue_declare(queue=RPC_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RPC_QUEUE, on_message_callback=on_rpc_request)

    print("InsultService RPC awaiting requests on 'insult_rpc_queue'...")
    channel.start_consuming()

def broadcaster():
    """ Cada 5 segons, envia un insult aleatori als clients via broadcast. """
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.exchange_declare(exchange=BROADCAST_EXCHANGE, exchange_type="fanout")

    while True:
        time.sleep(5)
        if insults:
            insult = random.choice(list(insults))
            message = json.dumps({"insult": insult})
            channel.basic_publish(exchange=BROADCAST_EXCHANGE, routing_key="", body=message)
            print(f"Broadcasted insult: {insult}")

def start_broadcaster():
    """ Executa el broadcaster en un thread. """
    thread = threading.Thread(target=broadcaster, daemon=True)
    thread.start()

def main():
    start_broadcaster()  # Inicia el broadcasting d'insults
    start_rpc_server()   # Inicia el servidor RPC per afegir insults

if __name__ == "__main__":
    main()
