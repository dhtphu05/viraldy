# Module Boundaries

Modules expose application contracts or public facades. Domain code does not import FastAPI, SQLAlchemy, Celery, Redis, boto3, HTTPX, or provider SDKs.

Cross-module communication uses stable IDs, application services, query ports, command handlers, and versioned internal events. Modules must not deep-import another module's infrastructure or ORM models.
