# insult_filter_rabbitmq.py
#!/usr/bin/env python3
import pika, redis, re, json, threading, time, unicodedata

# —— Redis for insults store
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

while True:
    try:
        r.ping()
        break
    except redis.exceptions.ConnectionError:
        time.sleep(1)

TEXTS_QUEUE  = 'text_queue'
RESULT_QUEUE = 'filtered_queue'
INSULTS_SET  = 'insults'
HISTORY_LIST = 'filtered_history'

def normalize(s):
    """Elimina tildes y diacríticos para normalizar."""
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

class RabbitFilter:
    def __init__(self, amqp_url='localhost'):
        # 1) Conexión RabbitMQ con retry hasta que el broker esté listo
        while True:
            try:
                self.conn = pika.BlockingConnection(pika.ConnectionParameters(amqp_url))
                break
            except pika.exceptions.AMQPConnectionError:
                time.sleep(1)
        self.ch   = self.conn.channel()
        self.ch.queue_declare(queue=TEXTS_QUEUE,  durable=True)
        self.ch.queue_declare(queue=RESULT_QUEUE, durable=True)
        self.ch.basic_qos(prefetch_count=50)

        # 2) Patrón combinado + refresco periódico
        self.lock    = threading.Lock()
        self.pattern = re.compile(r"$^")
        self.refresh_pattern()
        threading.Thread(target=self._refresher, daemon=True).start()


    def refresh_pattern(self):
        insults = [normalize(ins) for ins in r.smembers(INSULTS_SET)]
        if insults:
            esc = [re.escape(ins) for ins in insults]
            pat = r"\b(?:" + "|".join(esc) + r")\b"
            with self.lock:
                self.pattern = re.compile(pat, re.IGNORECASE)
        else:
            with self.lock:
                self.pattern = re.compile(r"$^")

    def _refresher(self):
        while True:
            time.sleep(5)
            self.refresh_pattern()

    def callback(self, ch, method, props, body):
        text = body.decode()
        if text.strip().lower() == 'lista':
            history = r.lrange(HISTORY_LIST, 0, -1)
            ch.basic_publish(
                exchange='', routing_key=props.reply_to,
                properties=pika.BasicProperties(correlation_id=props.correlation_id),
                body=json.dumps(history)
            )
        else:
            # aquí tu lógica de censura
            censored = self.pattern.sub(lambda m: '*' * len(m.group(0)), text)
            ch.basic_publish(
                exchange='',
                routing_key=props.reply_to,
                properties=pika.BasicProperties(correlation_id=props.correlation_id),
                body=censored
            )
        ch.basic_ack(delivery_tag=method.delivery_tag)


    def run(self):
        self.ch.basic_consume(queue=TEXTS_QUEUE, on_message_callback=self.callback)
        self.ch.start_consuming()

if __name__ == "__main__":
    RabbitFilter().run()
