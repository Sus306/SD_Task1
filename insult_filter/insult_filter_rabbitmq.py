# insult_filter_rabbitmq.py
import pika
import re

# Lista para almacenar textos filtrados (en memoria)
filtered_texts = []

# Lista de insultos a censurar
INSULTS = ["idiota", "estúpido", "imbécil", "tonto"]

def filter_text(text):
    """
    Reemplaza en el texto cada insulto por "CENSORED".
    """
    filtered = text
    for insult in INSULTS:
        filtered = re.sub(r'\b' + re.escape(insult) + r'\b', "CENSORED", filtered, flags=re.IGNORECASE)
    return filtered

def callback(ch, method, properties, body):
    text = body.decode()
    filtered = filter_text(text)
    filtered_texts.append(filtered)
    print(f"Filtered: '{text}' -> '{filtered}'")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_filter_worker():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    # Declaramos la cola de textos (durable)
    channel.queue_declare(queue="text_queue", durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="text_queue", on_message_callback=callback)
    print("InsultFilter awaiting messages in 'text_queue'...")
    channel.start_consuming()

if __name__ == "__main__":
    start_filter_worker()
