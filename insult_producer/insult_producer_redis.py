# insult_producer_redis.py
import redis
import time
import random

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
TEXTS_QUEUE = "texts_queue"

phrases = [
    "Hello, you are an idiota!",
    "What a tonto idea, absolutely stupid.",
    "I can't believe you acted like an imbecil.",
    "This is simply unacceptable, you are so estúpido.",
    "Normal phrase with no insults.",
    "idiota, really."
]

def produce_texts():
    while True:
        phrase = random.choice(phrases)
        r.rpush(TEXTS_QUEUE, phrase)
        print("Enviado:", phrase)
        time.sleep(3)

if __name__ == "__main__":
    produce_texts()
