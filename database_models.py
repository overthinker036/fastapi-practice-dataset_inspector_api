from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, JSON
Base = declarative_base()

class Analysis(Base):

    __tablename__ = "analysis"


    a_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    result = Column(JSON, nullable=True)
    error = Column(String, nullable=True)