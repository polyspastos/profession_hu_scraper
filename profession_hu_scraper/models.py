from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class JobModel(Base):
    __tablename__ = 'jobs'
    _id = Column(Integer, primary_key=True)

    position = Column(String, nullable=False)
    company = Column(String, nullable=False)
    address = Column(String)
    salary = Column(String)
    url = Column(String, nullable=False, unique=True)
    added_at = Column(String)