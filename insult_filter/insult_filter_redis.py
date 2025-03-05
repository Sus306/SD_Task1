import redis

redis_client = redis.StrictRedis(host='localhost', port=6379, db=1)

def filter_text_redis(text):
    filtered_text = text.replace("insult", "CENSORED")
    redis_client.rpush("filtered_texts", filtered_text)
    return filtered_text

def get_filtered_texts_redis():
    return redis_client.lrange("filtered_texts", 0, -1)