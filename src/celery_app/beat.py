from celery.schedules import crontab

beat_schedule = {
    "delete-expired-tokens": {
        "task": "celery_app.tasks.delete_expired_tokens",
        "schedule": crontab(minute="*/30"),
    },
}
