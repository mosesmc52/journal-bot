import os
from datetime import datetime, timedelta

import requests
import sqlalchemy
from sqlalchemy import orm
import gspread

import models
from google_drive import ( GoogleDrive )

class Conversation(object):

    def __init__(self, service_account_file, drive_folder_parent_id, history_file = './conversation.txt'):
        self.history_file = history_file

        # load google drive instance
        self.goog_drive = GoogleDrive(service_account_file = service_account_file )
        self.goog_sheet = gspread.service_account(filename= service_account_file)
        self.drive_folder_parent_id = drive_folder_parent_id

        # open sqllite db
        engine = sqlalchemy.create_engine('sqlite:///journal.db')
        self.db_session = orm.Session(bind=engine)

    def _get_folder(self):
        folder_name = datetime.now().strftime('%b %y')
        folder = self.db_session.query(models.Folder).filter( models.Folder.name == folder_name).first()

        if not folder:
        	response = self.goog_drive.create_folder(folder_name, self.drive_folder_parent_id)
        	folder = models.Folder(name = response.get('name'), goog_id =  response.get('id'))
        	self.db_session.add(folder)
        	self.db_session.commit()

        return folder

    def _get_day_doc(self, folder_parents_id):
        doc_name = datetime.now().strftime('%b %-d conversation')
        doc = self.db_session.query(models.Doc).filter( models.Doc.name == doc_name).first()
        if not doc:
        	response = self.goog_drive.create_document(doc_name, folder_parents_id = folder_parents_id)
        	doc = models.Doc(name = response.get('name'), goog_id =  response.get('id'))
        	self.db_session.add(doc)
        	self.db_session.commit()

        return doc

    def add_content(self, speaker ,message, category = '', is_bot = False ):
        folder = self._get_folder()

    	# save message to google docs
        doc = self._get_day_doc(folder_parents_id = folder.goog_id)

        if is_bot:
            text_color = '37be83'
            source = 'bot'
        else:
            text_color = '4e79a7'
            source = 'human'

        self.goog_drive.write_document(document_id = doc.goog_id, body = '{}:\n{}'.format(speaker, message), rgb_hex = text_color)

        # save conversation to sqllite
        conversation = models.Conversation(source = source, category=category, message = message)
        self.db_session.add(conversation)
        self.db_session.commit()

        with open(self.history_file, "a+") as myfile:
            myfile.write('{}:{}\n'.format(speaker, message))

    def add_media(url ,mimetype):
        folder = self._get_folder()

        # upload possible media
        r = requests.get(url, allow_redirects=True)

        file_name = '{}.{}'.format(datetime.now().strftime('%b-%-d-%Y-%-I-%M-%p'), mimetype.split('/')[-1])
        full_file_path = './media/{}'.format(file_name)
        open(full_file_path, 'wb').write(r.content)
        response = goog_drive.upload_media( full_file_path, mimetype, folder.goog_id)
        os.remove('./media/{}'.format(full_file_path))

        # add media  to sqllite
        media = models.Media(name = file_name, goog_id =  response.get('id'))
        self.db_session.add(media)
        self.db_session.commit()

    def get_entire_history(self):
        with open(self.history_file,mode='r+') as myfile:
            all_of_it = myfile.read()
        return all_of_it

    def total_messages(self, category = ''):
        conversations = self.db_session.query(models.Conversation).filter( models.Conversation.source == 'human', models.Conversation.category == category).all()
        if conversations:
            return len(conversations)

        return 0

    def has_journaled_today(self):
        doc = self.db_session.query(models.Doc).filter( models.Doc.name == doc_name).first()
        if doc:
            return True

        return False

    def latest_message(self):
        conversation = self.db_session.query(models.Conversation).filter().order_by(sqlalchemy.desc('date')).first()
        return conversation
