from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, CHAR
from sqlalchemy.orm import relationship, declarative_base
import re
from isbnlib import to_isbn13, is_isbn10, is_isbn13
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# engine = create_engine("mysql+pymysql://root:password@localhost/book_review")
# Session = sessionmaker(bind=engine)
# session = Session()
# Base.metadata.create_all(engine)

class Author(Base):
    __tablename__ = 'author'

    author_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    bio = Column(Text)
    birth_date = Column(Date)

    works = relationship("AuthorWork", back_populates="author")


class BookWork(Base):
    __tablename__ = 'book_work'

    work_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(150), nullable=False)
    description = Column(Text)

    editions = relationship("BookEdition", back_populates="work")
    authors = relationship("AuthorWork", back_populates="work")
    categories = relationship("Category", back_populates="work")


class AuthorWork(Base):
    __tablename__ = 'author_work'

    author_id = Column(Integer, ForeignKey('author.author_id'), primary_key=True)
    work_id = Column(Integer, ForeignKey('book_work.work_id'), primary_key=True)

    author = relationship("Author", back_populates="works")
    work = relationship("BookWork", back_populates="authors")


class BookEdition(Base):
    __tablename__ = 'book_edition'

    isbn13 = Column(CHAR(13), primary_key=True)
    isbn10 = Column(CHAR(10), unique=True)
    publish_year = Column(Integer)
    cover_id = Column(Integer)
    publisher_name = Column(String(100))
    work_id = Column(Integer, ForeignKey('book_work.work_id'))

    work = relationship("BookWork", back_populates="editions")


class Genre(Base):
    __tablename__ = 'genre'

    genre_id = Column(Integer, primary_key=True)
    genre_name = Column(String(100), unique=True, nullable=False)

    categories = relationship("Category", back_populates="genre")


class Category(Base):
    __tablename__ = 'category'

    genre_id = Column(Integer, ForeignKey('genre.genre_id'), primary_key=True)
    work_id = Column(Integer, ForeignKey('book_work.work_id'), primary_key=True)

    genre = relationship("Genre", back_populates="categories")
    work = relationship("BookWork", back_populates="categories")


def get_books_by_author_name(session, name_substring: str):
    """
    Return a list of BookWork objects written by authors whose name contains the given substring.
    """
    return (
        session.query(BookWork)
        .join(AuthorWork, BookWork.work_id == AuthorWork.work_id)
        .join(Author, AuthorWork.author_id == Author.author_id)
        .filter(Author.name.like(f"%{name_substring}%"))
        .all()
)

def get_books_by_genre_name(session, name_substring: str):
    """
    Return a list of BookWork objects written by authors whose name contains the given substring.
    """
    return (
        session.query(BookWork)
        .join(Category, BookWork.work_id == Category.work_id)
        .join(Genre, Category.genre_id == Genre.genre_id)
        .filter(Genre.genre_name.like(f"%{name_substring}%"))
        .all()
)

def get_books_by_title_name(session, name_substring: str):
    """
    Return a list of BookWork objects written by authors whose name contains the given substring.
    """
    return (
        session.query(BookWork)
        .filter(BookWork.title.like(f"%{name_substring}%"))
        .all()
)

def get_book_title_by_isbn(session, number: str):
    """
    Return a list of book title by isbn10 or isbn13.
    """
    isbn = normalize_isbn(number)
    return (
        session.query(BookWork)
        .join(BookEdition, BookWork.work_id == BookEdition.work_id)
        .filter(BookEdition.isbn13 == isbn)
        .all()
)

def normalize_isbn(isbn_raw):
    isbn = re.sub(r'[^0-9X]', '', isbn_raw.upper())  # remove dashes/spaces
    if is_isbn10(isbn):
        return to_isbn13(isbn)
    elif is_isbn13(isbn):
        return isbn
    else:
        return None
