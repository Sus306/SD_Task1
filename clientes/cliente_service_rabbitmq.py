# client_insult_subscriber_rabbitmq.py
import pika
import json

def callback(ch, method, properties, body):
    data = json.loads(body)
    print("Received broadcast insult:", data.get("insult"))

def start_subscriber():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    # Declarar el exchange fanout para recibir broadcast
    channel.exchange_declare(exchange="insult_broadcast", exchange_type="fanout")
    # Crear una cola temporal y exclusiva
    result = channel.queue_declare(queue="", exclusive=True)
    queue_name = result.method.queue
    channel.queue_bind(exchange="insult_broadcast", queue=queue_name)
    print("Client subscriber listening for broadcast insults...")
    channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

if __name__ == "__main__":
    start_subscriber()
