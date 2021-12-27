'''
Reference:
	crontab.scredules: configure
	https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html
'''

import os
import random

from celery import Celery
from celery.schedules import crontab
import redis
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv('.env')

from conversation import ( Conversation )

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379')
CELERY_TIMEZONE = os.environ.get('TIMEZONE', 'UTC')


TO_PHONE = os.environ.get('TO_PHONE', '')
FROM_PHONE = os.environ.get('FROM_PHONE', '')

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')

conversation = Conversation(service_account_file = os.getenv('SERVICE_ACCOUNT_FILE'), drive_folder_parent_id = os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID'))

# Initialize Celery and update its config
celery = Celery('journal-bot',
				broker = CELERY_BROKER_URL,
				backend = CELERY_RESULT_BACKEND
				)

# Add periodic tasks
celery_beat_schedule = {
	"heart_beat": {
		"task": "heart_beat",
		"schedule": crontab(minute='*/15')
	},
	"evening-checkin": {
		"task": "daily_checkin",
		"schedule": crontab(hour=18, minute=0)
	},
	"weekly-reflection-question": {
		"task": "reflection",
		"schedule": crontab(hour=13, minute=0, day_of_week='sunday')
	},
}

celery.conf.update(
	timezone=CELERY_TIMEZONE,
	task_serializer="json",
	accept_content=["json"],
	result_serializer="json",
	beat_schedule=celery_beat_schedule,
)

@celery.task(name="evening_checkin")
def daily_checkin():

	messages = [
		'How are doing?'
	]
	if not conversation.has_journaled_today():
		# select random index from message
		random_index = random.randint(0,len(messages)-1)
		conversation.add_content(os.getenv('BOT_NAME'), messages[random_index], category = 'experience', is_bot = True)

		# send message to studio to trigger stream of messages
		client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
		message = client.messages.create(
                              body=messages[random_index],
                              from_=FROM_PHONE,
                              to=TO_PHONE
                          )

	return True

@celery.task(name="reflection")
def reflection():
	m_count = total_messages(category = 'reflection')

	question_file = open("reflection-questions.txt", "r")
	questions = fp.read().split('\n')
	if m_count < len(questions):

		conversation.add_content(os.getenv('BOT_NAME'), questions[m_count].strip(), category = 'reflection', is_bot = True)

		# send message to studio to trigger stream of messages
		client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
		message = client.messages.create(
                              body=messages[random_index],
                              from_=FROM_PHONE,
                              to=TO_PHONE
                          )

	return True

@celery.task(name="heart_beat")
def heart_beat():
	return 'beep'
