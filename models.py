# This is for creating the tables in DataBase

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from database import Base
from sqlalchemy.orm import relationship


class Questions(Base):
    __tablename__='questions'

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(String, index=True)

    choices = relationship("Choices", back_populates="questions")


class Choices(Base):
    __tablename__='choices'

    id = Column(Integer, primary_key=True, index=True)
    choice_text = Column(String, index=True)
    is_correct = Column(Boolean, default=False)
    question_id = Column(Integer, ForeignKey("questions.id"))

    questions = relationship("Questions", back_populates = "choices")