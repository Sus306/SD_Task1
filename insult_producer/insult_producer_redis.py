import redis
import time
import json

# Conexión a Redis (localhost:6379, db 0)
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

TEXTS_QUEUE = "texts_queue"
RESULTS_QUEUE = "filtered_texts"
HISTORY_KEY = "filtered_history"

# Lista de frases de ejemplo, incluyendo el comando especial "lista"
phrases = [
    "Hello, you are an idiota!",
    "What a tonto idea, absolutely stupid.",
    "I can't believe you acted like an imbecil.",
    "This is simply unacceptable, you are so estúpido.",
    "Normal phrase with no insults.",
    "idiota, really."
]

def produce_texts():
    for phrase in phrases:
        text = phrase.strip()
        # Enviar comando "lista" o texto normal
        r.rpush(TEXTS_QUEUE, text)

        if text.lower() == "lista":
            print("\n[Comando 'lista' enviado al filtro]")
            # Espera la respuesta (JSON con historial)
            _, payload = r.blpop(RESULTS_QUEUE)
            payload_str = payload if isinstance(payload, str) else payload.decode()
            try:
                history = json.loads(payload_str)
            except json.JSONDecodeError:
                print("Error: no se pudo decodificar el historial recibido.")
                continue

            if not history:
                print("No hay frases filtradas aún.")
            else:
                print("Historial de frases filtradas:")
                for idx, h in enumerate(history, 1):
                    print(f" {idx}. {h}")
        else:
            print(f"\nEnviado para filtrar: {text}")
            # Espera la frase censurada del filtro
            _, filtered = r.blpop(RESULTS_QUEUE)
            filtered_text = filtered if isinstance(filtered, str) else filtered.decode()
            print(f"Recibido censurado: {filtered_text}")

        time.sleep(3)

if __name__ == "__main__":
    produce_texts()
