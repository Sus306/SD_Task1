import Pyro4

@Pyro4.expose
class InsultServicePyRO:
    def __init__(self):
        self.insults = set()

    def add_insult(self, insult):
        if insult not in self.insults:
            self.insults.add(insult)
            return f"Insult '{insult}' added."
        return "Insult already exists."

    def get_insults(self):
        return list(self.insults)

daemon = Pyro4.Daemon()
uri = daemon.register(InsultServicePyRO)
print(f"PyRO Server running at {uri}")
daemon.requestLoop()