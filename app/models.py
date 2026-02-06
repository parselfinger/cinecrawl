"""SQLAlchemy ORM models for the database schema."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    imdb_id = Column(String(255), nullable=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    release_year = Column(Integer, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)
    poster_url = Column(String(2048), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    showtimes = relationship(
        "Showtime", back_populates="movie", cascade="all, delete-orphan"
    )


class Cinema(Base):
    __tablename__ = "cinemas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    verbose_location = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    showtimes = relationship(
        "Showtime", back_populates="cinema", cascade="all, delete-orphan"
    )


class Showtime(Base):
    __tablename__ = "showtimes"

    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(
        Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False
    )
    cinema_id = Column(Integer, ForeignKey("cinemas.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    screen_type = Column(String(255), default="2D")
    movie_url = Column(String(2048), nullable=True)

    # Relationships
    movie = relationship("Movie", back_populates="showtimes")
    cinema = relationship("Cinema", back_populates="showtimes")
