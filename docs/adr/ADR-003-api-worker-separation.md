# ADR-003 API Worker Separation

FastAPI is the stateless control plane. Celery workers are the compute plane. Heavy media/AI work must not run inside request handlers.
