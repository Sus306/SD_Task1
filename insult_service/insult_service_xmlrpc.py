import xmlrpc.server

class InsultServiceXMLRPC:
    def __init__(self):
        self.insults = set()

    def add_insult(self, insult):
        if insult not in self.insults:
            self.insults.add(insult)
            return f"Insult '{insult}' added."
        return "Insult already exists."

    def get_insults(self):
        return list(self.insults)

server = xmlrpc.server.SimpleXMLRPCServer(("localhost", 8000))
server.register_instance(InsultServiceXMLRPC())
print("XML-RPC Server running on port 8000...")
server.serve_forever()