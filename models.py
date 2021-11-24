from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database import Base

class Folder(Base):
    __tablename__ = 'folder'

    id = Column(Integer, primary_key = True)
    name = Column(String(20), unique = True)
    goog_id = Column(String(20), unique = True)
    date = Column(DateTime)

    def __init__(self, security_type = None, goog_id = None):
        self.name = name
        self.goog_id = goog_id

class Doc(Base):
    __tablename__ = 'doc'
    parent_folder_id = Column(Integer, ForeignKey('folder.id'))
    id = Column(Integer, primary_key = True)
    name = Column(String(20), unique = True)
    goog_id = Column(String(20), unique = True)
    date = Column(DateTime)

    def __init__(self, security_type = None, goog_id = None):
        self.name = name
        self.goog_id = goog_id

class Media(Base):
    __tablename__ = 'media'
    parent_folder_id = Column(Integer, ForeignKey('folder.id'))
    id = Column(Integer, primary_key = True)
    name = Column(String(20), unique = True)
    goog_id = Column(String(20), unique = True)
    date = Column(DateTime)

    def __init__(self, security_type = None, goog_id = None):
        self.name = name
        self.goog_id = goog_id
