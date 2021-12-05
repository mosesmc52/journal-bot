from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from database import Base

class Folder(Base):
	__tablename__ = 'folder'

	id = Column(Integer, primary_key = True)
	name = Column(String(20))
	goog_id = Column(String(20), unique = True)
	date = Column(DateTime)

	def __init__(self, name = None,  goog_id = None):
		self.name = name
		self.goog_id = goog_id
		self.date = datetime.now()

class Doc(Base):
	__tablename__ = 'doc'
	parent_folder_id = Column(Integer, ForeignKey('folder.id'))
	id = Column(Integer, primary_key = True)
	name = Column(String(20))
	goog_id = Column(String(20), unique = True)
	date = Column(DateTime)

	def __init__(self, name = None, goog_id = None):
		self.name = name
		self.goog_id = goog_id
		self.date = datetime.now()

class Media(Base):
	__tablename__ = 'media'
	parent_folder_id = Column(Integer, ForeignKey('folder.id'))
	id = Column(Integer, primary_key = True)
	name = Column(String(20))
	goog_id = Column(String(20), unique = True)
	date = Column(DateTime)

	def __init__(self, name = None, goog_id = None):
		self.name = name
		self.goog_id = goog_id
		self.date = datetime.now()


class Conversation(Base):
	__tablename__ = 'conversation'
	id = Column(Integer, primary_key = True)
	source = Column(String(20))
	category = Column(String(20))
	message = Column(Text)
	date = Column(DateTime)

	def __init__(self, source = None, message = None, category = ''):
		self.source = source
		self.message = message
		self.category = category
		self.date = datetime.now()
