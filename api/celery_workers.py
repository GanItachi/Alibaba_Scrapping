from celery import Celery

# Connexion à Redis comme broker
celery_app = Celery(
    "tasks",
    broker="redis://redis_cache:6379/0",
    backend="redis://redis_cache:6379/0"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json"
)

