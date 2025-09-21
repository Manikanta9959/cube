# app/models.py
from typing import Optional
from pydantic import BaseModel, Field
from datetime import date
from sqlalchemy import Column, Integer, String, Date, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ReviewORM(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, index=True)
    rating = Column(Integer)
    text = Column(Text)
    date = Column(String)

class ReviewCreate(BaseModel):
    id: int
    location: str
    rating: int
    text: str
    date: str

class ReviewOut(ReviewCreate):
    sentiment: Optional[str] = None
    topics: Optional[list] = []
