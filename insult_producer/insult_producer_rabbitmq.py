import pika
import uuid
import random
import time

texts = [
    "Hello, you are an idiota!",
    "What a tonto idea, absolutely stupid.",
    "I can't believe you acted like an imbecil.",
    "This is simply unacceptable, you are so estúpido.",
    "Normal phrase with no insults.",
    "idiota, really."
]

class Producer:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        # Assegura que la cua per enviar textos existeix
        self.channel.queue_declare(queue="text_queue", durable=True)

        # Crear la cua de resposta per rebre missatges del filter
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True
        )

        self.response = None
        self.corr_id = None

    def on_response(self, ch, method, props, body):
        """ Processa la resposta del filtre """
        if self.corr_id == props.correlation_id:
            self.response = body.decode()

    def send_text(self, text):
        """ Envia una frase a la cua de filtres i espera la resposta. """
        self.response = None
        self.corr_id = str(uuid.uuid4())

        self.channel.basic_publish(
            exchange='',
            routing_key="text_queue",
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,  # Assegura que la resposta arriba aquí
                correlation_id=self.corr_id,
                delivery_mode=2
            ),
            body=text
        )

        print(f"Sent to filter: {text}")

        while self.response is None:
            self.connection.process_data_events()

        return self.response

    def start(self):
        """ Envia frases contínuament i espera la resposta del filtre """
        while True:
            phrase = random.choice(texts)
            filtered_text = self.send_text(phrase)
            print(f"Filtered response: {filtered_text}")
            time.sleep(3)

if __name__ == "__main__":
    producer = Producer()
    producer.start()
