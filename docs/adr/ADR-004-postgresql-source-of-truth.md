# ADR-004 PostgreSQL Source Of Truth

PostgreSQL stores durable business state. Redis is queue, coordination, and cache only. No job, result, or session state is stored in process RAM.
