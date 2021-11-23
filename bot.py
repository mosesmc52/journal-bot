import os
from datetime import datetime, timedelta
import json
from flask import Flask, request
from dotenv import load_dotenv
from celery import Celery
import sqlalchemy
from sqlalchemy import orm
import models

from google_drive import ( GoogleDrive )

# load environmental variables
load_dotenv('.env')

# load google drive instance
goog_drive = GoogleDrive(os.getenv('SERVICE_ACCOUNT_FILE'))

# open sqllite db
engine = sqlalchemy.create_engine('sqlite:///journal.db')
db_session = orm.Session(bind=engine)

app = Flask(__name__)

@app.route('/', methods=['GET'])
def helloworld():
	return 'Hi, I\'m {}. I help you remember your life.'.format(os.getenv('BOT_NAME'))

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
