# inproducer_redis.py

import xmlrpc.client
import time

# Lista de frases de ejemplo que contienen insultos
phrases = [
    "You are an idiota and a fool.",
    "What a tonto idea, absolutely stupid.",
    "I can't believe you acted like an imbecil.",
    "This is simply unacceptable, you are so estúpido.",
    "Normal phrase with no insults.",
    "idiota, really."
]

def produce_phrases(filter_server_url="http://127.0.0.1:8001"):
    """
    Envía cada frase al InsultFilter para que sea filtrada.
    """
    filter_service = xmlrpc.client.ServerProxy(filter_server_url, allow_none=True)
    
    for phrase in phrases:
        print("Frase original:", phrase)
        try:
            filtered = filter_service.filter_phrase(phrase)
            print("Frase filtrada:", filtered)
        except Exception as e:
            print("Error al filtrar la frase:", e)
        time.sleep(3)  # Pausa de 3 segundos entre frases

if __name__ == "__main__":
    produce_phrases()
