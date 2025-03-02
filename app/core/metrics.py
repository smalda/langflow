import time

from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Define metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"]
)

DB_CONNECTION_GAUGE = Gauge(
    "db_connections_active", "Number of active database connections"
)

QUEUE_MESSAGE_COUNT = Counter(
    "queue_messages_total", "Total messages processed", ["queue_name", "status"]
)


def setup_metrics(app: FastAPI):
    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method, endpoint=request.url.path
        ).observe(duration)

        return response

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app
