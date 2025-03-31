import pika
import json
import uuid
import threading

class InsultClient:
    def __init__(self):
        """ Inicialitza el client RabbitMQ amb connexions separades per RPC i Broadcast. """
        self.rpc_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.rpc_channel = self.rpc_connection.channel()

        # Cua RPC temporal per rebre respostes
        result = self.rpc_channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue
        self.rpc_channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True
        )

        self.response = None
        self.corr_id = None

        # Configurar la connexió per escoltar insults en broadcast
        self.broadcast_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.broadcast_channel = self.broadcast_connection.channel()
        self.broadcast_channel.exchange_declare(exchange="insult_broadcast", exchange_type="fanout")

        result = self.broadcast_channel.queue_declare(queue="", exclusive=True)
        self.queue_name = result.method.queue
        self.broadcast_channel.queue_bind(exchange="insult_broadcast", queue=self.queue_name)
        self.broadcast_channel.basic_consume(queue=self.queue_name, on_message_callback=self.on_broadcast, auto_ack=True)

    def on_response(self, ch, method, props, body):
        """ Captura la resposta RPC. """
        if self.corr_id == props.correlation_id:
            self.response = json.loads(body)

    def call(self, command, data=None):
        """ Envia una petició RPC al InsultService. """
        self.response = None
        self.corr_id = str(uuid.uuid4())
        request = json.dumps({"command": command, "data": data})

        self.rpc_channel.basic_publish(
            exchange='',
            routing_key='insult_rpc_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id
            ),
            body=request
        )

        while self.response is None:
            self.rpc_connection.process_data_events()

        return self.response

    def on_broadcast(self, ch, method, properties, body):
        """ Rep insults de RabbitMQ cada 5 segons i els mostra. """
        try:
            data = json.loads(body)
            print(f"Received broadcast insult: {data.get('insult')}")
        except json.JSONDecodeError:
            print("Error decoding message:", body)

    def start_listening(self):
        """ Escolta insults de broadcast contínuament. """
        print("Listening for insults from service...")
        self.broadcast_channel.start_consuming()

def main():
    client = InsultClient()

    # Inicia un thread per escoltar insults en broadcast
    thread = threading.Thread(target=client.start_listening, daemon=True)
    thread.start()

    while True:
        insult = input("Enter insult to send to the service (or 'exit'): ")
        if insult.lower() == "exit":
            break
        response = client.call("add_insult", insult)
        print("Response from service:", response)

if __name__ == "__main__":
    main()
