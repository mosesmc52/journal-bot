from sqlalchemy import Column, Integer, String, DateTime
from database import Base

class Doc(Base):
    __tablename__ = 'doc'

    id = Column(Integer, primary_key = True)
    name = Column(String(20), unique = True)
    goog_doc_id = Column(String(20), unique = True)
    date = Column(DateTime)

    def __init__(self, security_type = None, goog_doc_id = None):
        self.name = name
        self.goog_doc_id = goog_doc_id
