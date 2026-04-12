from prometheus_client import Histogram, Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

# Feed enrichment latency histogram
feed_enrich_latency_seconds = Histogram(
    'feed_enrich_latency_seconds',
    'Feed enrichment API latency in seconds',
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0, 2.0]
)

# Feed enrichment request counter
feed_enrich_requests_total = Counter(
    'feed_enrich_requests_total',
    'Total number of feed enrichment requests',
    ['emotion_context', 'frugal_mode']
)

# Redis cache hit/miss counter
redis_cache_hits_total = Counter(
    'redis_cache_hits_total',
    'Total number of Redis cache hits'
)

redis_cache_misses_total = Counter(
    'redis_cache_misses_total',
    'Total number of Redis cache misses'
)


def metrics_endpoint():
    """
    Prometheus metrics endpoint
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
