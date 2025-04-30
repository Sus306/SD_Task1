#!/usr/bin/env python3
import pika
import uuid
import json
import time

# Lista de frases a enviar al filtro, incluyendo el comando especial 'lista'
texts = [
    "Hello, you are an idiota!",
    "What a tonto idea, absolutely stupid.",
    "I can't believe you acted like an imbecil.",
    "This is simply unacceptable, you are so estúpido.",
    "Normal phrase with no insults.",
    "idiota, really."
]

class Producer:
    def __init__(self, amqp_url='localhost'):
        # Conexión al broker y configuración de colas
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(amqp_url))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue="text_queue", durable=True)

        # Cola exclusiva para recibir respuestas RPC
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
        # Procesa la respuesta del filtro
        if self.corr_id == props.correlation_id:
            self.response = body.decode()

    def send_text(self, text):
        # Publica el texto con correlation_id y queue de respuesta
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key="text_queue",
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
                delivery_mode=2
            ),
            body=text
        )
        # Espera la respuesta
        while self.response is None:
            self.connection.process_data_events()
        return self.response

    def start(self):
        # Envía cada frase y procesa respuestas
        for phrase in texts:
            resp = self.send_text(phrase)

            if phrase.strip().lower() == 'lista':
                print("\n[Comando 'lista' enviado: mostrando historial de frases filtradas]")
                try:
                    history = json.loads(resp)
                except json.JSONDecodeError:
                    print("Error al decodificar historial recibido.")
                    continue

                if not history:
                    print("No hay frases filtradas aún.")
                else:
                    print("Historial de frases filtradas:")
                    for idx, entry in enumerate(history, 1):
                        print(f" {idx}. {entry}")
            else:
                print(f"Enviado al filtro: {phrase}")
                print(f"Respuesta filtrada: {resp}")

            time.sleep(3)

        self.connection.close()

if __name__ == "__main__":
    producer = Producer()
    producer.start()
