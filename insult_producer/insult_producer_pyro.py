import Pyro4
import time
import random

# Lista de frases de ejemplo (algunas contienen insultos)
phrases = [
    "You are an idiota and a fool.",
    "What a tonto idea, absolutely stupid.",
    "I can't believe you acted like an imbecil.",
    "This is simply unacceptable, you are so estúpido.",
    "Normal phrase with no insults.",
    "idiota, really."
]

def produce_phrases():
    # Conectar al InsultFilter a través del Name Server
    ns = Pyro4.locateNS()
    filter_uri = ns.lookup("insult.filter")
    filter_service = Pyro4.Proxy(filter_uri)
    
    for phrase in phrases:
        print("Frase original:", phrase)
        try:
            filtered = filter_service.filter_text(phrase)
            print("Frase filtrada:", filtered)
        except Exception as e:
            print("Error al filtrar la frase:", e)
        time.sleep(3)

if __name__ == "__main__":
    produce_phrases()
