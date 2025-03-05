import pika

def filter_callback(ch, method, properties, body):
    text = body.decode()
    filtered_text = text.replace("insult", "CENSORED")
    print(f"Filtered text: {filtered_text}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.queue_declare(queue='filter')
channel.basic_consume(queue='filter', on_message_callback=filter_callback)
print("RabbitMQ Filter Service is running...")
channel.start_consuming()