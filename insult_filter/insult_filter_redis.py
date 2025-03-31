import redis
import time
import re

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

TEXTS_QUEUE = "texts_queue"
RESULTS_QUEUE = "filtered_texts"
INSULTS_KEY = "insults"

def filter_text(text, insults):
    for insult in insults:
        pattern = re.compile(re.escape(insult), re.IGNORECASE)
        text = pattern.sub("***", text)
    return text

def process_texts():
    while True:
        _, text = r.blpop(TEXTS_QUEUE)
        insults = r.smembers(INSULTS_KEY)
        filtered_text = filter_text(text, insults)

        # Retorna la frase filtrada al producer
        r.rpush(RESULTS_QUEUE, filtered_text)
        print(f"Text filtrat: '{text}' -> '{filtered_text}'")

def main():
    print("InsultFilter (Redis Work Queue) en ejecución...")
    process_texts()

if __name__ == "__main__":
    main()
