# insult_service_rabbitmq.py

import pika
import threading
import time
import random
import json
import redis

# Conexión a Redis (localhost:6379, db 0)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
INSULTS_KEY = "insults"

# Configuración de RabbitMQ
BROADCAST_EXCHANGE = "insult_broadcast"
RPC_QUEUE = "insult_rpc_queue"
params = pika.ConnectionParameters('localhost')

def add_insult(insult):
    """Agrega un insulto a Redis si no existe."""
    added = r.sadd(INSULTS_KEY, insult)
    if added:
        print(f"Insult added to Redis: {insult}")
        return f"Insult '{insult}' added successfully."
    else:
        return f"Insult '{insult}' already exists."

def get_insults():
    """Recupera la lista de insultos desde Redis."""
    return list(r.smembers(INSULTS_KEY))

def on_rpc_request(ch, method, props, body):
    """Gestiona las solicitudes RPC (add_insult / get_insults)."""
    try:
        request = json.loads(body)
        command = request.get("command")
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
            body=json.dumps(response)
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"Error processing RPC request: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag)

def start_rpc_server():
    """Inicia el servidor RPC en la cola insult_rpc_queue."""
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=RPC_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RPC_QUEUE, on_message_callback=on_rpc_request)
    print("InsultService RPC awaiting requests on 'insult_rpc_queue'...")
    channel.start_consuming()

def broadcaster():
    """Cada 5 segundos, difunde un insulto aleatorio (desde Redis) a través de fanout."""
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.exchange_declare(exchange=BROADCAST_EXCHANGE, exchange_type="fanout")
    while True:
        time.sleep(5)
        insults = list(r.smembers(INSULTS_KEY))
        if insults:
            insult = random.choice(insults)
            message = json.dumps({"insult": insult})
            channel.basic_publish(exchange=BROADCAST_EXCHANGE, routing_key="", body=message)
            print(f"Broadcasted insult: {insult}")

def main():
    # Arranca el broadcaster en hilo
    threading.Thread(target=broadcaster, daemon=True).start()
    # Arranca el servidor RPC
    start_rpc_server()

if __name__ == "__main__":
    main()
