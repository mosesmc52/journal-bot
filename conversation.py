import os
import random
from datetime import datetime, timedelta

import giphy_client
import gspread
import models
import requests
import sqlalchemy
from giphy_client.rest import ApiException as GiphyApiException
from google_drive import GoogleDrive
from sqlalchemy import desc, orm


class Conversation(object):
    def __init__(
        self,
        service_account_file,
        drive_folder_parent_id,
        glphy_api_key,
        training_data_file="./conversational-training-data.txt",
        reflection_question_data_file="reflection-questions.txt",
    ):
        self.training_data_file = training_data_file
        self.reflection_question_data_file = reflection_question_data_file

        # load google drive instance
        self.goog_drive = GoogleDrive(service_account_file=service_account_file)
        self.goog_sheet = gspread.service_account(filename=service_account_file)
        self.drive_folder_parent_id = drive_folder_parent_id

        # open sqllite db
        engine = sqlalchemy.create_engine("sqlite:///journal.db")
        self.db_session = orm.Session(bind=engine)
        self.glphy_api = giphy_client.DefaultApi()
        self.glphy_api_key = glphy_api_key
        self.GLIPHY_MAX_OFFSET = 100
        self.GLIPHY_LIMIT = 100

    def get_random_glphy_gif(self, query):

        random_limit = random.randint(0, self.GLIPHY_LIMIT)
        random_offset = random.randint(0, self.GLIPHY_MAX_OFFSET)

        try:
            response = self.glphy_api.gifs_search_get(
                self.glphy_api_key, query, limit=random_limit, offset=random_offset
            )
        except GiphyApiException as e:
            print("Exception when calling DefaultApi->gifs_search_get: %s\n" % e)

        return response.data[0].images.fixed_height.url

    def _get_folder(self):
        folder_name = datetime.now().strftime("%b %y")
        folder = (
            self.db_session.query(models.Folder)
            .filter(models.Folder.name == folder_name)
            .first()
        )

        if not folder:
            response = self.goog_drive.create_folder(
                folder_name, self.drive_folder_parent_id
            )
            folder = models.Folder(
                name=response.get("name"), goog_id=response.get("id")
            )
            self.db_session.add(folder)
            self.db_session.commit()

        return folder

    def _get_day_doc(self, folder_parents_id):
        doc_name = datetime.now().strftime("%b %-d conversation")
        doc = (
            self.db_session.query(models.Doc)
            .filter(models.Doc.name == doc_name)
            .first()
        )
        if not doc:
            response = self.goog_drive.create_document(
                doc_name, folder_parents_id=folder_parents_id
            )
            doc = models.Doc(name=response.get("name"), goog_id=response.get("id"))
            self.db_session.add(doc)
            self.db_session.commit()

        return doc

    def add_content(self, speaker, message, category="", is_bot=False):
        folder = self._get_folder()

        # save message to google docs
        doc = self._get_day_doc(folder_parents_id=folder.goog_id)

        if is_bot:
            text_color = "37be83"
            source = "bot"
        else:
            text_color = "4e79a7"
            source = "human"

        self.goog_drive.write_document(
            document_id=doc.goog_id,
            body="{}:\n{}".format(speaker, message),
            rgb_hex=text_color,
        )

        # save conversation to sqllite
        conversation = models.Conversation(
            source=source, category=category, message=message
        )
        self.db_session.add(conversation)
        self.db_session.commit()

    def add_media(self, url, mimetype):
        folder = self._get_folder()

        # upload possible media
        r = requests.get(url, allow_redirects=True)

        file_name = "{}.{}".format(
            datetime.now().strftime("%b-%-d-%Y-%-I-%M-%p"), mimetype.split("/")[-1]
        )
        full_file_path = "./media/{}".format(file_name)
        open(full_file_path, "wb").write(r.content)
        response = self.goog_drive.upload_media(
            full_file_path, mimetype, folder.goog_id
        )
        os.remove(full_file_path)

        # add media  to sqllite
        media = models.Media(name=file_name, goog_id=response.get("id"))
        self.db_session.add(media)
        self.db_session.commit()

    def add_content_to_tranining_data(self, speaker, message):
        with open(self.training_data_file, "a+") as myfile:
            myfile.write("{}:{}\n".format(speaker, message))

    def get_training_data(self):
        with open(self.training_data_file, mode="r+") as myfile:
            all_of_it = myfile.read()
        return all_of_it

    def total_messages(self, category=""):
        conversations = (
            self.db_session.query(models.Conversation)
            .filter(
                models.Conversation.source == "human",
                models.Conversation.category == category,
            )
            .all()
        )
        if conversations:
            return len(conversations)

        return 0

    def has_journaled_today(self):
        doc_name = datetime.now().strftime("%b %-d conversation")
        doc = (
            self.db_session.query(models.Doc)
            .filter(models.Doc.name == doc_name)
            .first()
        )
        if doc:
            return True

        return False

    def has_reflected_today(self):
        doc_name = datetime.now().strftime("%b %-d conversation")
        conversation = (
            self.db_session.query(models.Conversation)
            .filter(models.Conversation.category == "reflection")
            .order_by(desc("date"))
            .first()
        )
        if conversation:
            if conversation.date.date() == datetime.now().date():
                return True

        return False

    def latest_message(self):
        conversation = (
            self.db_session.query(models.Conversation)
            .filter()
            .order_by(desc("date"))
            .first()
        )
        return conversation

    def get_reflection_question(self):
        # get total number of questions
        with open(self.reflection_question_data_file, "r") as fp:
            questions = fp.read().split("\n")
            random_question = random.randint(0, len(questions) - 1)
            return questions[random_question].strip()
