from celery import Celery
from config.settings import settings

celery_app = Celery(
    "cinema",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["celery_app.tasks"]
)

celery_app.config_from_object("celery_app.beat")

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
)