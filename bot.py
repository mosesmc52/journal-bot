import os
import random

import json
from flask import Flask, request
from dotenv import load_dotenv

import openai

from conversation import ( Conversation )
from utils import ( period_of_day, hasPhrase )

app = Flask(__name__)

# find on https://docs.sentry.io/error-reporting/quickstart/?platform=python
# load environmental variables
load_dotenv('.env')

# Load OpenAI Library
openai.api_key =os.getenv('OPENAPI_API_KEY')

conversation = Conversation(service_account_file = os.getenv('SERVICE_ACCOUNT_FILE'), drive_folder_parent_id = os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID'))

# initialize sentry
if os.getenv('SENTRY_DSN', None):
	import sentry_sdk
	from sentry_sdk import capture_exception
	sentry_sdk.init(dsn=os.getenv('SENTRY_DSN'))

@app.route('/', methods=['GET'])
def helloworld():
	return '''Hi, I\'m {}. I here to help you keep track of your memories in life.'''.format(os.getenv('BOT_NAME'))

@app.route('/greeting', methods=['POST'])
def greeting():
	memory = json.loads(request.form['Memory'])
	period = period_of_day(os.getenv('TIMEZONE'))
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
			'Good evening, How are doing?'
		]

	# select random index from message
	random_index = random.randint(0,len(messages)-1)
	conversation.add_content(os.getenv('BOT_NAME'), messages[random_index], is_bot = True)

	return {
	      "actions": [
	        	{
	              "collect": {
	                  "name": "response",
	                  "questions": [
	                      {
	                          "question": {
	                              "say": messages[random_index]
	                          },
	                          "name": "response"
	                      }
	                  ],
	                  "on_complete": {
	                      "redirect": "task://share-experience"
	                  }
	              },
	          },
			  {
				  "remember": {
					  "first_name": os.getenv('MY_FIRST_NAME'),
					  "category": 'experience'
				  }
			  }
	      ]
	    }

@app.route('/share/experience', methods=['POST'])
def share_experience():
	memory = json.loads(request.form['Memory'])


	if memory['twilio'].get('collected_data'): # handles input after greeting
		answer = memory['twilio']['collected_data']['response']['answers']['response']['answer']
		if memory['twilio']['collected_data']['response']['answers']['response'].get('media', None):
			mimetype = memory['twilio']['collected_data']['response']['answers']['response']['media']['type']
			url  = memory['twilio']['collected_data']['response']['answers']['response']['media']['url']
			conversation.add_media(url = url, mimetype = mimetype)

		category = memory.get('category','experience')
	else: # handles fallback input
		answer = request.form.get('CurrentInput')
		if memory.get('media', None):
			mimetype = memory['media']['type']
			url  = memory['media']['url']
			conversation.add_media(url = url, mimetype = mimetype)

		latest_message = conversation.latest_message()
		if latest_message:
			category = latest_message.category or 'experience'
		else:
			category = 'experience'


	if answer.lower() in ['no', 'nothing','none'] or hasPhrase(phrases = ['nothing else', 'i\'m good'], text = answer.lower()):
		message =  "Thanks for sharing. Talk to you later"
		return {
					"actions": [
						{
							"say": message
						}
					]
				}

	conversation.add_content('me', answer, category = category)

	messages = [
				'Is there anything else you would like to tell me?',
				'** blink ** I want to hear more. Tell me  :)'
				]

	random_index = random.randint(0,len(messages)-1)
	conversation.add_content(os.getenv('BOT_NAME'), messages[random_index], category = category, is_bot = True)

	return {
	      "actions": [
	        	{
	              "collect": {
	                  "name": "response",
	                  "questions": [
	                      {
	                          "question": {
	                              "say": message
	                          },
	                          "name": "response"
	                      }
	                  ],
	                  "on_complete": {
	                      "redirect": "task://share-experience"
	                  }
	              }
				  }
	      ]
	    }

@app.route('/share/idea', methods=['POST'])
def share_idea():
	user_input = request.form.get('CurrentInput')
	conversation.add_content('me', user_input)

	message = 'Please share your idea. I\'m exicted to hear!'
	conversation.add_content(os.getenv('BOT_NAME'), message, is_bot = True)

	return {
	      "actions": [
	        	{
	              "collect": {
	                  "name": "response",
	                  "questions": [
	                      {
	                          "question": {
	                              "say": message
	                          },
	                          "name": "response"
	                      }
	                  ],
	                  "on_complete": {
	                      "redirect": "task://share-experience"
	                  }
	              },
	          },
			  {
				  "remember": {
					  "category": 'idea'
				  }
			  }
	      ]
	    }

@app.route('/gratitude', methods=['POST'])
def gratitude():
	user_input = request.form.get('CurrentInput')
	conversation.add_content('me', user_input, category = 'gratitude')

	message = 'Thanks for sharing. It\'s always good to be thankful!'
	conversation.add_content(os.getenv('BOT_NAME'), message, is_bot = True)

	return {
		"actions": [
			{
				"say": message
			}
		]
	}

@app.route('/question', methods=['POST'])
def openai_response():
	user_input = request.form.get('CurrentInput')
	conversation.add_content_to_tranining_data('me', user_input)
	training_data = conversation.get_training_data()

	response = openai.Completion.create(
	  engine="davinci",
	  prompt=training_data,
	  temperature=0.4, # This setting controls the randomness of the generated text.  0 deterministic, 1 random baby
	  max_tokens=60,
	  top_p=1,
	  frequency_penalty=0.5,	# Prevents word repetitions
	  presence_penalty=0, # Prevent topics repetitions
	  stop=["me:"]
	)

	random_index = random.randint(0,len( response.choices)-1)
	message = response.choices[random_index].text.replace('{}:'.format(os.getenv('BOT_NAME')), '')
	conversation.add_content_to_tranining_data(os.getenv('BOT_NAME'), message)

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

@app.route('/fallback', methods=['POST'])
def fallback():
	current_input = request.form.get('CurrentInput').lower()
	tokens = current_input.split(' ')
	if tokens[0] in ['who', 'did', 'whose', 'which', 'where', 'when', 'why', 'how', 'what']:
		return {
			"actions": [
				{
					"redirect": "task://question"
				}
			]
		}

	return {
				"actions": [
					{
						"redirect": "task://share-experience"
					}
				]
			}

if __name__ == '__main__':
	app.run()
