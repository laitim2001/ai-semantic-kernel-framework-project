"""runtime — execution plane (workers, scheduling, queue backends).

Distinct from agent_harness/ (the loop logic itself) and platform_layer/
(cross-cutting middleware). runtime/ owns HOW the loop is executed
(in-process / Celery / Temporal / cron).
"""
