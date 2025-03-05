import redis

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

def add_insult_redis(insult):
    if not redis_client.sismember("insults", insult):
        redis_client.sadd("insults", insult)
        return f"Insult '{insult}' added."
    return "Insult already exists."

def get_insults_redis():
    return list(redis_client.smembers("insults"))