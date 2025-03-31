import pika
import re
import json
import uuid

class FilterWorker:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        # Configura la cua on rep els textos a filtrar
        self.channel.queue_declare(queue="text_queue", durable=True)

    def get_insults(self):
        """ Obté insults del servei InsultService via RPC. """
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()

        # Cua temporal per a RPC
        result = channel.queue_declare(queue='', exclusive=True)
        callback_queue = result.method.queue

        channel.basic_publish(
            exchange='',
            routing_key='insult_rpc_queue',
            properties=pika.BasicProperties(
                reply_to=callback_queue,
                correlation_id=str(uuid.uuid4())
            ),
            body=json.dumps({"command": "get_insults"})
        )

        # Espera resposta
        for method, properties, body in channel.consume(callback_queue, inactivity_timeout=5):
            if method:
                channel.basic_ack(method.delivery_tag)
                channel.cancel()
                connection.close()
                return json.loads(body)

        channel.cancel()
        connection.close()
        return []

    def filter_text(self, text, insults):
        """ Filtra els insults d'una frase """
        for insult in insults:
            pattern = re.compile(re.escape(insult), re.IGNORECASE)
            text = pattern.sub("***", text)
        return text

    def callback(self, ch, method, properties, body):
        """ Processa els textos rebuts, els filtra i retorna el resultat. """
        text = body.decode()
        insults = self.get_insults()  # Obté insults actualitzats
        filtered_text = self.filter_text(text, insults)

        if properties.reply_to and isinstance(properties.reply_to, str):
            ch.basic_publish(
                exchange='',
                routing_key=properties.reply_to,  # Ens assegurem que és una cadena
                properties=pika.BasicProperties(correlation_id=properties.correlation_id),
                body=filtered_text
            )
            print(f"Filtered: '{text}' -> '{filtered_text}'")
        else:
            print(f"Error: No reply_to found or invalid value for message: {text}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def start(self):
        """ Escolta missatges i els processa """
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue="text_queue", on_message_callback=self.callback)
        print("Filter Worker started. Waiting for messages...")
        self.channel.start_consuming()

if __name__ == "__main__":
    worker = FilterWorker()
    worker.start()
