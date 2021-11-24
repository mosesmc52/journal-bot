import os
import random
from datetime import datetime, timedelta
import json

from flask import Flask, request
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import orm
import openai
import gspread

import models
from google_drive import ( GoogleDrive )
from conversation import ( Conversation )
from utils import ( period_of_day )

app = Flask(__name__)

# find on https://docs.sentry.io/error-reporting/quickstart/?platform=python
# load environmental variables
load_dotenv('.env')

# Load OpenAI Library
openai.api_key =os.getenv('OPENAPI_API_KEY')

# load google drive instance
goog_drive = GoogleDrive(os.getenv('SERVICE_ACCOUNT_FILE'))
goog_sheet = gspread.service_account(filename=os.getenv('SERVICE_ACCOUNT_FILE'))

# open sqllite db
engine = sqlalchemy.create_engine('sqlite:///journal.db')
db_session = orm.Session(bind=engine)

conversation = Conversation()

# initialize sentry
if os.getenv('SENTRY_DSN', None):
	import sentry_sdk
	from sentry_sdk import capture_exception
	sentry_sdk.init(dsn=os.getenv('SENTRY_DSN'))

  # Add Redis URL configurations
if os.getenv('CELERY_BROKER_URL', None):
	from celery import Celery
	import redis
	app.config["CELERY_BROKER_URL"] =  os.getenv('CELERY_BROKER_URL', None)
	app.config["CELERY_RESULT_BACKEND"] =  os.getenv('CELERY_BROKER_URL', None)

	# Connect Redis db
	redis_db = redis.Redis(
	  host="redis", port="6379", db=1, charset="utf-8", decode_responses=True
	)

	# Initialize timer in Redis
	redis_db.mset({"minute": 0, "second": 0})

	# Add periodic tasks
	celery_beat_schedule = {
	}

	# Initialize Celery and update its config
	celery = Celery(app.name)
	celery.conf.update(
		result_backend=app.config["CELERY_RESULT_BACKEND"],
		broker_url=app.config["CELERY_BROKER_URL"],
		timezone="UTC",
		task_serializer="json",
		accept_content=["json"],
		result_serializer="json",
		beat_schedule=celery_beat_schedule,
	)



@app.route('/', methods=['GET'])
def helloworld():
	return '''Hi, I\'m {}. I here to help you keep track of your memories in life.'''.format(os.getenv('BOT_NAME'))

@app.route('/greeting', methods=['POST'])
def greeting():
	memory = json.loads(request.form['Memory'])
	period = period_of_day()
	first_name = os.getenv('MY_FIRST_NAME', '')
	user_input = request.form.get('CurrentInput')

	conversation.add_content('me', user_input)

	if period == 'morning':
		messages = [
			'Morning, *smile* How are you doing luv?'
		]
	elif period in ['noon', 'afternoon']:
		messages = [
			'Good to hear from you, *smile* How are you doing luv?'
		]
	elif period == 'evening':
		messages = [
			'Good evening, Are you having a good time?'
		]

	# select random index from message
	random_index = random.randint(0,len(messages)-1)
	conversation.add_content(os.getenv('BOT_NAME'), messages[random_index])

	return {
			"actions": [
					{
						"say": messages[random_index]
					},
					{
						"remember": {
							"first_name": first_name,
						}
					},
					{
						"listen": True
					}
				]
			}

@app.route('/share/photo', methods=['POST'])
def share_photo():
	pass

@app.route('/share/audio', methods=['POST'])
def share_audio():
	pass

@app.route('/share/video', methods=['POST'])
def share_video():
	pass

@app.route('/share/experience', methods=['POST'])
def share_experience():
	pass

@app.route('/share/idea', methods=['POST'])
def share_idea():
	pass

@app.route('/gratitude', methods=['POST'])
def gratitude():
	pass

@app.route('/goal', methods=['POST'])
def goal():
	pass

@app.route('/question', methods=['POST'])
@app.route('/fallback', methods=['POST'])
def openai_response():
	user_input = request.form.get('CurrentInput')
	conversation.add_content('me', user_input)
	prompt = conversation.get_entire_history()

	response = openai.Completion.create(
	  engine="davinci",
	  prompt=prompt,
	  temperature=0.4, # This setting controls the randomness of the generated text.  0 deterministic, 1 random baby
	  max_tokens=60,
	  top_p=1,
	  frequency_penalty=0.5,	# Prevents word repetitions
	  presence_penalty=0, # Prevent topics repetitions
	  stop=["me:"]
	)

	random_index = random.randint(0,len( response.choices)-1)
	message = response.choices[random_index].text.replace('{}:'.format(os.getenv('BOT_NAME')), '')
	conversation.add_content(os.getenv('BOT_NAME'), message)

	return {
			"actions": [
					{
						"say": message
					},
					{
						"listen": True
					}
				]
			}

#@celery.task
#def prompt():
#    pass

#@celery.task
#def morning_checkin():
#    pass

#@celery.task
#def evening_checkin():
#    pass


if __name__ == '__main__':
	app.run()
