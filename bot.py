from datetime import datetime, timedelta
import json
import os
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv('.env')

app = Flask(__name__)

@app.route('/', methods=['GET'])
def helloworld():
	return 'Hi, I\'m Samantha. I help you remember your life.'

@app.route('/greeting', methods=['POST'])
def greeting():
    pass

@app.route('/share/photo', methods=['POST'])
def share_photo():
    pass

@app.route('/share/audio', methods=['POST'])
def share_audio():
    pass

@app.route('/share/video', methods=['POST'])
def share_video():
    pass

@app.route('/share/audio', methods=['POST'])
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
def question():
    pass

@app.route('/prompt', methods=['POST'])
def prompt():
    pass


if __name__ == '__main__':
	app.run()
