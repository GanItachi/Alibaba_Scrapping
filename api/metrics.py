from prometheus_client import Counter, Histogram
from fastapi import Request
import time

# Compteur du nombre total de requêtes
REQUEST_COUNT = Counter(
    "api_requests_total", "Total des requêtes HTTP reçues", ["method", "endpoint"]
)

# Histogramme pour mesurer le temps de réponse des requêtes
REQUEST_LATENCY = Histogram(
    "api_request_duration_seconds", "Temps de réponse des requêtes", ["endpoint"]
)

# Middleware pour enregistrer les métriques
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    endpoint = request.url.path
    method = request.method

    REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()
    REQUEST_LATENCY.labels(endpoint=endpoint).observe(process_time)

    return response
