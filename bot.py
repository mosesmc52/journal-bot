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

@app.route('/share/photo', methods=['POST'])
def share_photo():
	memory = json.loads(request.form['Memory'])
	period = period_of_day()
	user_input = request.form.get('CurrentInput')



@app.route('/share/audio', methods=['POST'])
def share_audio():
	memory = json.loads(request.form['Memory'])
	period = period_of_day()
	user_input = request.form.get('CurrentInput')


@app.route('/share/video', methods=['POST'])
def share_video():
	memory = json.loads(request.form['Memory'])
	period = period_of_day()
	user_input = request.form.get('CurrentInput')

@app.route('/share/experience', methods=['POST'])
def share_experience():
	memory = json.loads(request.form['Memory'])

	answer = memory['twilio']['collected_data']['response']['answers']['response']['answer']
	if answer.lower() in ['no', 'nothing','none'] or hasPhrase(phrases = ['nothing else', 'i\'m good'], text = answer.lower()):
		message =  "Thanks for sharing. Talk to you later"
		return {
					"actions": [
						{
							"say": message
						}
					]
				}

	conversation.add_content('me', answer, category = memory.get('category','experience'))

	if memory['twilio']['collected_data']['response']['answers']['response'].get('media', None):
		mimetype = memory['twilio']['collected_data']['response']['answers']['response']['media']['type']
		url  = memory['twilio']['collected_data']['response']['answers']['response']['media']['url']
		conversation.add_media(url = url, mimetype = mimetype)

	message = 'Is there anything else you would like to tell me?'
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
	conversation.add_content(os.getenv('BOT_NAME'), message, is_bot = True)

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
def prompt():
	questions = [
		'Who are you?',
		'What are your dreams?',
		'What thought keep you from living in the present?',
		'What\'s your passion?',
		'How do you feel talking about sex with others? Why do you think you feel this way?',
		'How do you want to be remembered?',
		'What principles do you lead your life by?',
		'Do you believe in a higher bieng?',
		'What\'s are your thouhgts on meditation? Are you open to trying it?',
		'What habits do you need to let go of?',
		'What habits should you adopt?',
		'What is something you\'ve wanted to do, but were turned down for by friends or family? What advice did they give you?',
		'What is your favorite book? Why did its message resonte with you?',
		'If you were to write a book, what would it be about? What message do you want to deliver to the world?',
		'What is the best compliment you have ever recieved? Why did it leave such a lasting impression of you? What does this tell about yourself?',
		'How much do you trust yourself around others? How genuine are you in social settings? Describe a moment in which you were fully able to be you in a group setting?',
		'Describe an instance where this was true for you. What advice would you give your past self now?',
		'What makes you laugh the most?',
		'Describe your thoughts on life after death.',
		'What are your feeling about contraception?',
		'Feminism?',
		'Are you pro-life or pro-choice? Why?',
		'What\'s more important talent or hard work',
		'How much control do you think you have over your fate?',
		'Describe your relax routine.',
		'How strong is your faith in your government or community?',
		'What\'s your opinion on patriotism?',
		'How cometitive are you? Do you tink you need to change that? What made you this way?',
		'When was the last time you thought you would fail, but you ultimately succeeded? What message would you give to your detractors?'
	]

if __name__ == '__main__':
	app.run()
