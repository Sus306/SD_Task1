#!/usr/bin/env python3
import redis
import time
import re
import json

# Conexión a Redis (localhost:6379, db 0)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Nombres de colas y claves
TEXTS_QUEUE   = "texts_queue"
RESULTS_QUEUE = "filtered_texts"
INSULTS_KEY   = "insults"
HISTORY_KEY   = "filtered_history"


def filter_text(text, insults):
    """Reemplaza cada insulto por "***"."""
    for insult in insults:
        pattern = re.compile(r"\b" + re.escape(insult) + r"\b", re.IGNORECASE)
        text = pattern.sub("***", text)
    return text


def process_texts():
    # Limpiar colas de entrada, salida e historial al arrancar (mantiene el set de insultos)
    r.delete(TEXTS_QUEUE, RESULTS_QUEUE, HISTORY_KEY)
    print("InsultFilter Redis iniciado. Colas e historial limpios.")
    while True:
        _, raw = r.blpop(TEXTS_QUEUE)
        txt = raw if not isinstance(raw, bytes) else raw.decode()
        cmd = txt.strip().lower()

        # Comando "lista": devolver historial completo
        if cmd == "lista":
            history = r.lrange(HISTORY_KEY, 0, -1)
            r.rpush(RESULTS_QUEUE, json.dumps(history))
            print("Comando 'lista' procesado: enviado historial completo")
            continue

        # Filtrado normal
        insults = r.smembers(INSULTS_KEY)
        censored = filter_text(txt, insults)

        # Publicar resultado y guardar en historial
        r.rpush(RESULTS_QUEUE, censored)
        r.rpush(HISTORY_KEY, censored)
        print(f"Filtrado: '{txt}' -> '{censored}'")


if __name__ == "__main__":
    process_texts()
