import pika
import re
import json
import uuid

class FilterWorker:
    def __init__(self, amqp_url='localhost'):
        # Conexión para recibir tareas
        self.conn   = pika.BlockingConnection(pika.ConnectionParameters(amqp_url))
        self.ch     = self.conn.channel()
        self.ch.queue_declare(queue='text_queue', durable=True)

        # Conexión separada para RPC con el InsultService
        self.rpc_conn   = pika.BlockingConnection(pika.ConnectionParameters(amqp_url))
        self.rpc_ch     = self.rpc_conn.channel()

        # Historial de frases filtradas
        self.filtered_texts = []

    def get_insults(self):
        """Lanza un RPC get_insults y espera la respuesta correlacionada."""
        corr_id = str(uuid.uuid4())
        result     = self.rpc_ch.queue_declare(queue='', exclusive=True)
        callback_q = result.method.queue

        self.rpc_ch.basic_publish(
            exchange='',
            routing_key='insult_rpc_queue',
            properties=pika.BasicProperties(
                reply_to=callback_q,
                correlation_id=corr_id
            ),
            body=json.dumps({"command": "get_insults"})
        )

        while True:
            method_frame, props, body = self.rpc_ch.basic_get(callback_q, auto_ack=True)
            if method_frame and props.correlation_id == corr_id:
                try:
                    return json.loads(body)
                finally:
                    self.rpc_ch.queue_delete(queue=callback_q)

    def callback(self, ch, method, props, body):
        """Filtra el texto recibido o devuelve el historial si recibe 'lista'."""
        text = body.decode()
        text_clean = text.strip().lower()

        # Si viene el comando 'lista', devolver historial completo
        if text_clean == 'lista':
            payload = json.dumps(self.filtered_texts)
            if props.reply_to:
                ch.basic_publish(
                    exchange='',
                    routing_key=props.reply_to,
                    properties=pika.BasicProperties(correlation_id=props.correlation_id),
                    body=payload
                )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print("Comando 'lista' procesado: enviado historial de frases filtradas")
            return

        # Filtrado normal
        insults = self.get_insults()
        filtered = text
        for insult in insults:
            filtered = re.compile(re.escape(insult), re.IGNORECASE).sub("***", filtered)

        # Guardar en historial
        self.filtered_texts.append(filtered)

        # Responder texto filtrado
        if props.reply_to:
            ch.basic_publish(
                exchange='',
                routing_key=props.reply_to,
                properties=pika.BasicProperties(correlation_id=props.correlation_id),
                body=filtered
            )
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"Text filtrat: '{text}' -> '{filtered}'")

    def start(self):
        """Arranca el worker de filtrado."""
        self.ch.basic_qos(prefetch_count=1)
        self.ch.basic_consume(queue='text_queue', on_message_callback=self.callback)
        print("Filter Worker (RabbitMQ) started. Waiting for messages…")
        self.ch.start_consuming()

if __name__ == "__main__":
    worker = FilterWorker()
    worker.start()
