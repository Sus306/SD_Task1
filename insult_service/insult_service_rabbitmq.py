import pika

def insult_callback(ch, method, properties, body):
    insult = body.decode()
    print(f"Received insult: {insult}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.queue_declare(queue='insults')
channel.basic_consume(queue='insults', on_message_callback=insult_callback)
print("RabbitMQ Insult Service is running...")
channel.start_consuming()