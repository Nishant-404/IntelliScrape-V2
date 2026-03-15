from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    site = relationship("Site", uselist=False, back_populates="owner")


class Site(Base):
    __tablename__ = "sites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    home_url = Column(String, nullable=False)
    login_url = Column(String, nullable=True)
    target_username = Column(String, nullable=True)
    target_password = Column(String, nullable=True)
    last_scraped_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="site")
    pages = relationship("RawPage", back_populates="site", cascade="all, delete-orphan")
    chunks = relationship("ProcessedChunk", back_populates="site", cascade="all, delete-orphan")


class RawPage(Base):
    __tablename__ = "raw_pages"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), index=True, nullable=False)
    url = Column(String, index=True, nullable=False)
    status_code = Column(Integer, nullable=True)
    headers_json = Column(Text, nullable=True)
    html = Column(Text, nullable=True)
    content_hash = Column(String, nullable=True)
    changed = Column(Boolean, default=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    site = relationship("Site", back_populates="pages")


class ProcessedChunk(Base):
    __tablename__ = "processed_chunks"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), index=True, nullable=False)
    source_url = Column(String, index=True, nullable=False)
    tag = Column(String, nullable=True)
    chunk_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    site = relationship("Site", back_populates="chunks")
