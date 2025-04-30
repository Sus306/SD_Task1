# insult_filter/insult_filter_redis.py

import redis
import time
import re
import json

# Conexión a Redis (localhost:6379, db 0)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

TEXTS_QUEUE   = "texts_queue"
RESULTS_QUEUE = "filtered_texts"
INSULTS_KEY   = "insults"
HISTORY_KEY   = "filtered_history"

def filter_text(text, insults):
    """ Reemplaza cada insulto por "***". """
    for insult in insults:
        pattern = re.compile(r'\b' + re.escape(insult) + r'\b', re.IGNORECASE)
        text = pattern.sub("***", text)
    return text

def process_texts():
    # limpiamos historial al arrancar
    r.delete(HISTORY_KEY)
    while True:
        _, raw = r.blpop(TEXTS_QUEUE)
        txt = raw.decode() if isinstance(raw, bytes) else raw
        cmd = txt.strip().lower()
        if cmd == "lista":
            # devolvemos todo el historial en JSON
            history = r.lrange(HISTORY_KEY, 0, -1)
            r.rpush(RESULTS_QUEUE, json.dumps(history))
            print("Comando 'lista' procesado: enviado historial completo")
        else:
            insults  = r.smembers(INSULTS_KEY)
            censored = filter_text(txt, insults)
            # respuesta al producer
            r.rpush(RESULTS_QUEUE, censored)
            # guardamos en el histórico
            r.rpush(HISTORY_KEY, censored)
            print(f"Filtrado: '{txt}' -> '{censored}'")

if __name__ == "__main__":
    print("InsultFilter Redis iniciado...")
    process_texts()
