import redis
import threading
import time
import random

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

INSULTS_KEY = "insults"
BROADCAST_CHANNEL = "insults_channel"

def add_insult(insult):
    if r.sadd(INSULTS_KEY, insult):
        print(f"Insulto '{insult}' guardado en Redis.")
    else:
        print(f"Insulto '{insult}' ya estaba en Redis.")

def broadcaster():
    while True:
        insults = list(r.smembers(INSULTS_KEY))
        if insults:
            insult = random.choice(insults)
            r.publish(BROADCAST_CHANNEL, insult)
            print(f"Publicado insulto: {insult}")
        time.sleep(5)


def main():
    threading.Thread(target=broadcaster, daemon=True).start()
    print("InsultService Redis iniciado.")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
