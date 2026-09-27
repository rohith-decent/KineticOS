from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from api.database import Base
import datetime

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SessionDB(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    sets = relationship("SetDB", back_populates="session")

class SetDB(Base):
    __tablename__ = "sets"
    id = Column(String, primary_key=True, index=True) # set_id uuid/string
    session_id = Column(Integer, ForeignKey("sessions.id"))
    exercise = Column(String)
    load_kg = Column(Float)
    total_reps = Column(Integer)
    report_data = Column(JSON) # Stores B3 SetReport JSON output
    session = relationship("SessionDB", back_populates="sets")

