# Decision Log

## ADR-001: FastAPI over Flask/Django
**Date:** 2024-01  
**Decision:** Use FastAPI  
**Rationale:** Native async support, automatic OpenAPI docs, Pydantic validation, and Python 3.11 type hints are first-class. Django would add unnecessary ORM abstraction; Flask lacks built-in validation.

## ADR-002: PostgreSQL over SQLite/MySQL
**Decision:** PostgreSQL  
**Rationale:** Production-grade, excellent JSON support (for payload/condition columns), robust index types, and aligns with real manufacturing software stacks.

## ADR-003: Celery + Redis over APScheduler
**Decision:** Celery with Redis broker  
**Rationale:** Celery enables distributed workers, retry logic, result backends, and beat scheduling in a single framework. APScheduler is simpler but doesn't scale horizontally and lacks proper task isolation.

## ADR-004: Alembic for migrations
**Decision:** Alembic  
**Rationale:** Industry standard for SQLAlchemy projects. Versioned, reversible migrations with a clear upgrade/downgrade path. Alternatives like `create_all()` are fine for dev but dangerous in production.

## ADR-005: Event sourcing pattern for factory floor
**Decision:** Append-only `events` table  
**Rationale:** Manufacturing events are naturally immutable audit records. Side effects (station status, WO status) are applied synchronously on ingest. This gives both real-time state and a full historical audit log.

## ADR-006: Rule-based automation over ML
**Decision:** Rule-based JSON-configurable rules  
**Rationale:** For a portfolio project, explainable deterministic rules are more appropriate than black-box ML. The rule schema is extensible to add ML-scored conditions in the future.
