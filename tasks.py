'''
Reference:
Twillio Studio API: https://www.twilio.com/docs/studio/rest-api/execution
'''

import os
import json
import random

from celery import Celery
from celery.schedules import crontab
import redis
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv('.env')

from conversation import ( Conversation )
from utils import ( period_of_day )

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379'),
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379')
CELERY_TIMEZONE = os.environ.get('TIMEZONE', 'UTC')


TO_PHONE = os.environ.get('TO_PHONE', '')
FROM_PHONE = os.environ.get('FROM_PHONE', '')

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')

TWILIO_CHECKIN_FLOW_ID = os.environ.get('TWILIO_CHECKIN_FLOW', '')
TWILIO_REFLECTION_FLOW_ID = os.environ.get('TWILIO_REFLECTION_FLOW', '')


conversation = Conversation(service_account_file = os.getenv('SERVICE_ACCOUNT_FILE'), drive_folder_parent_id = os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID'))

# Initialize Celery and update its config
celery = Celery('journal-bot',
				broker = CELERY_BROKER_URL,
				backend = CELERY_RESULT_BACKEND
				)

# Add periodic tasks
celery_beat_schedule = {
	"evening-checkin": {
		"task": "daily_checkin",
		"schedule": crontab(hour=7, minute=0)
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
def daily_checkin():

	messages = [
		'How are doing?'
	]
	if not conversation.has_journaled_today():
		# select random index from message
		random_index = random.randint(0,len(messages)-1)
		conversation.add_content(os.getenv('BOT_NAME'), messages[random_index], is_bot = True)

		# send message to studio to trigger stream of messages
		client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
		execution = client.studio \
	                  .v1 \
	                  .flows(TWILIO_CHECKIN_FLOW_ID) \
	                  .executions \
	                  .create(
					  		to=TO_PHONE,
					  		from_=FROM_PHONE,
							parameters=json.loads({'message': messages[random_index]}))

	return True

@celery.task(name="reflection")
def reflection():
	m_count = total_messages(category = 'reflection')

	question_file = open("reflection-questions.txt", "r")
	questions = fp.read().split('\n')
	if m_count < len(questions):

		conversation.add_content(os.getenv('BOT_NAME'), questions[m_count].strip(), is_bot = True)

		# send message to studio to trigger stream of messages
		client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
		execution = client.studio \
	                  .v1 \
	                  .flows(TWILIO_CHECKIN_FLOW_ID) \
	                  .executions \
	                  .create(
					  		to=TO_PHONE,
					  		from_=FROM_PHONE,
							parameters=json.loads({'message': questions[m_count].strip()}))

	return True
