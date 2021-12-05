import os
from celery import Celery
from celery.schedules import crontab
import redis


from dotenv import load_dotenv
load_dotenv('.env')

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379')
CELERY_TIMEZONE = os.environ.get('TIMEZONE', 'UTC')

# Initialize Celery and update its config
celery = Celery('journal-bot',
				broker = CELERY_BROKER_URL,
				backend = CELERY_RESULT_BACKEND
				)

# Add periodic tasks
celery_beat_schedule = {
	"evening-checkin": {
		"task": "evening_checkin",
		"schedule": 5 #crontab(hour=7, minute=0)
	}
}

celery.conf.update(
	timezone=CELERY_TIMEZONE,
	task_serializer="json",
	accept_content=["json"],
	result_serializer="json",
	beat_schedule=celery_beat_schedule,
)

@celery.task(name="evening_checkin")
def evening_checkin():
	print('checkin')
	return True
