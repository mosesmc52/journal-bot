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



if __name__ == '__main__':
	app.run()
