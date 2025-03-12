# insult_producer_rabbitmq.py
import pika
import time
import random

texts = [
    "Hello, you are an idiota!",
    "What a tonto idea, absolutely stupid.",
    "I can't believe you acted like an imbecil.",
    "This is simply unacceptable, you are so estúpido.",
    "Normal phrase with no insults.",
    "idiota, really."
]

def start_producer():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    # Asegurarse de que la cola existe (durable)
    channel.queue_declare(queue="text_queue", durable=True)
    while True:
        text = random.choice(texts)
        channel.basic_publish(
            exchange="",
            routing_key="text_queue",
            body=text.encode(),
            properties=pika.BasicProperties(delivery_mode=2))
        print("Sent:", text)
        time.sleep(3)
    connection.close()

if __name__ == "__main__":
    start_producer()
