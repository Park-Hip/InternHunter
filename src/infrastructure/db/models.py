from sqlalchemy import Column, Integer, Boolean, String, JSON, Float, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()    

class RawJobDB(Base):
    __tablename__ = 'raw_jobs'
    id = Column(Integer, primary_key=True, autoincrement=True)

    url = Column(String, unique=True, nullable=False)
    title = Column(String)
    company = Column(String)
    location = Column(String) 

    full_json_dump = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    clean_job = relationship("CleanJobDB", back_populates="raw_job", uselist=False, cascade="all, delete-orphan")

class CleanJobDB(Base):
    __tablename__ = "clean_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_job_id = Column(Integer, ForeignKey("raw_jobs.id"), unique=True)     

    standardized_title = Column(String, index=True)
    job_level = Column(String)
    is_internship = Column(Boolean, default=False)

    description = Column(Text)
    requirement = Column(Text) 
    benefit = Column(Text) 

    cities = Column(JSON) 

    experience = Column(Float, nullable=True) 
    min_gpa = Column(Float, nullable=True)
    english_requirement = Column(String, nullable=True) 

    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    currency = Column(String, default="VND")
    is_salary_negotiable = Column(Boolean, default=False)

    tech_stack = Column(JSON)             # Tools: ["Python", "AWS"]
    technical_competencies = Column(JSON) # Actions: ["Deploy Models", "Fine-tune LLMs"]
    domain_knowledge = Column(JSON)       # Context: ["Banking", "E-commerce, NLP, Computer Vision, LLM, RAG"]

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    raw_job = relationship("RawJobDB", back_populates="clean_job")
    
