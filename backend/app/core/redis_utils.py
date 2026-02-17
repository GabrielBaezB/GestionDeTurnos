
import redis
import os

# Use Redis URL from env or default to localhost
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# In Docker verify the host is 'redis' if creating network, but 'localhost' for local dev.
# For docker-compose logic, we use 'redis' hostname usually.
# However, the env var should handle it.

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    print(f"Warning: Redis connection failed: {e}")
    redis_client = None

def get_next_ticket_number(queue_prefix: str) -> str:
    """
    Atomically increment the ticket counter for a specific queue prefix.
    Returns formatted string like 'V-001'.
    
    Key: ticket_counter:{prefix}:{YYYY-MM-DD}
    """
    if not redis_client:
        # Fallback or error? For now, raise logic error as Redis is required for SRE refactor.
        raise RuntimeError("Redis client not available for atomic counter")

    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    key = f"ticket_counter:{queue_prefix}:{today_str}"
    
    # INCR is atomic
    count = redis_client.incr(key)
    
    # Optional: Set expiry for 24h + buffer to auto-cleanup old keys
    # redis_client.expire(key, 86400 * 2) 

    return f"{queue_prefix}-{count:03d}"
