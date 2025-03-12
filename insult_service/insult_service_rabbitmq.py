# insult_service_rabbitmq.py
import pika
import threading
import time
import random
import json

# Conjunto para almacenar insultos (sin duplicados)
insults = set()

# Configuración del exchange para difusión
BROADCAST_EXCHANGE = "insult_broadcast"

# Conexión a RabbitMQ
params = pika.ConnectionParameters('localhost')

def add_insult(insult):
    """
    Agrega un insulto si no existe.
    """
    if insult not in insults:
        insults.add(insult)
        print(f"Insult added: {insult}")
        return f"Insult '{insult}' added successfully."
    else:
        return f"Insult '{insult}' already exists."

def get_insults():
    """
    Retorna la lista de insultos.
    """
    return list(insults)

def on_rpc_request(ch, method, props, body):
    """
    Función para procesar solicitudes RPC.
    El mensaje se espera sea un JSON con campos "command" y opcionalmente "data".
    Comandos:
      - "add_insult": Agrega un insulto.
      - "get_insults": Retorna la lista de insultos.
    """
    request = json.loads(body)
    command = request.get("command")
    response = None

    if command == "add_insult":
        response = add_insult(request.get("data"))
    elif command == "get_insults":
        response = get_insults()
    else:
        response = "Unknown command"

    ch.basic_publish(
        exchange="",
        routing_key=props.reply_to,
        properties=pika.BasicProperties(correlation_id=props.correlation_id),
        body=json.dumps(response))
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_rpc_server():
    """
    Inicia el servidor RPC para el InsultService en la cola 'insult_rpc_queue'.
    """
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue="insult_rpc_queue")
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="insult_rpc_queue", on_message_callback=on_rpc_request)
    print("InsultService RPC awaiting requests on 'insult_rpc_queue'...")
    channel.start_consuming()

def broadcaster():
    """
    Cada 5 segundos, elige un insulto aleatorio y lo difunde a través de un exchange fanout.
    """
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
    # connection.close()  # Nunca se llega aquí

def start_broadcaster():
    thread = threading.Thread(target=broadcaster, daemon=True)
    thread.start()

def main():
    start_broadcaster()
    start_rpc_server()

if __name__ == "__main__":
    main()
