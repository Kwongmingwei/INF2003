import mysql.connector
from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, CHAR, Numeric
from sqlalchemy.orm import relationship, declarative_base
import re
from isbnlib import to_isbn13, is_isbn10, is_isbn13
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

from nosql_service import get_aggregate_rating_for_work

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='dev',  # change this
        password='password',  # change this
        database='book_review',
        charset='utf8mb4'
    )

Base = declarative_base()

#engine = create_engine("mysql+pymysql://{changethis}:{passwordofyourthing}@localhost/book_review")
engine = create_engine("mysql+pymysql://dev:password@localhost/book_review")
Session = sessionmaker(bind=engine)
session = Session()
Base.metadata.create_all(engine)

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
    avg_rating = Column(Numeric(3, 2))

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

def _calculate_and_stage_update(work_id: int, db_session) -> bool:
    """
    Calculates rating by calling the get_aggregate_rating_for_work from nosql_service.py
    and stages the change in the SQLAlchemy session WITHOUT committing.
    """
    work_to_update = db_session.query(BookWork).get(work_id)
    if not work_to_update:
        logging.error(f"No book_work found with work_id: {work_id}")
        return False

    # Get list of all ISBN13 strings associated with work_id
    isbn_query_result = db_session.query(BookEdition.isbn13).filter_by(work_id=work_id).all()
    list_of_isbns = [item[0] for item in isbn_query_result]

    # Call get_aggregate_rating_for_work to get the aggregate stats
    stats = get_aggregate_rating_for_work(list_of_isbns)

    if not stats:
        work_to_update.avg_rating = None
        return True # Correctly determined there is no rating.

    total_sum = stats.get('total_rating_sum', 0)
    total_count = stats.get('total_review_count', 0)

    if total_count > 0:
        work_to_update.avg_rating = total_sum / total_count
    else:
        work_to_update.avg_rating = None

    return True


def get_work_id_for_isbn(db_session, isbn13: str):
    """
    Finds the work_id associated with a given ISBN13.
    """
    if not isbn13:
        return None
    result = db_session.query(BookEdition.work_id).filter_by(isbn13=isbn13).first()
    return result[0] if result else None


def update_work_rating(work_id: int):
    """
    This is our main trigger function. It creates a new session,
    recalculates the average rating for a single work, and commits the change.
    """
    if not work_id:
        logging.warning("update_work_rating called with no work_id.")
        return

    # Use a new session to ensure the operation is self-contained.
    db_session = Session()
    try:
        if _calculate_and_stage_update(work_id, db_session):
            db_session.commit()
            logging.info(f"Successfully updated avg_rating for work_id: {work_id}")
        else:
            db_session.rollback()
    except Exception as e:
        logging.error(f"Failed to update rating for work_id {work_id}: {e}")
        db_session.rollback()
    finally:
        db_session.close()

def fetch_all_genres():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT genre_name FROM genre ORDER BY genre_name")
    genres = [row['genre_name'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return genres


def fetch_top_genres():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT g.genre_name, COUNT(*) as count
        FROM genre g
        JOIN category c ON g.genre_id = c.genre_id
        GROUP BY g.genre_name
        ORDER BY count DESC
        LIMIT 15;
    """)
    genres = [row['genre_name'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return genres

def fetch_books_from_db(query=None, field="title", genres=None, year_from =None, year_to=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT bw.work_id, bw.title,bw.avg_rating, be.publish_year, GROUP_CONCAT(DISTINCT a.name SEPARATOR ', ') AS authors, GROUP_CONCAT(DISTINCT g.genre_name SEPARATOR ', ') AS genres
        FROM book_work bw
        LEFT JOIN author_work aw ON bw.work_id = aw.work_id
        LEFT JOIN author a ON a.author_id = aw.author_id
        LEFT JOIN category c ON c.work_id = bw.work_id
        LEFT JOIN genre g ON g.genre_id = c.genre_id
        LEFT JOIN book_edition be ON be.work_id = bw.work_id
    """

    conditions = []
    params = []

    if query:
        if field == "title":
            conditions.append("bw.title LIKE %s")
            params.append(f"%{query}%")
        elif field == "author":
            conditions.append("a.name LIKE %s")
            params.append(f"%{query}%")

    if genres:
        genre_placeholders = ','.join(['%s'] * len(genres))
        conditions.append(f"g.genre_name IN ({genre_placeholders})")
        params.extend(genres)
        
    if year_from:
        conditions.append("be.publish_year >= %s")
        params.append(year_from)
    
    if year_to:
        conditions.append("be.publish_year <= %s")
        params.append(year_to)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " GROUP BY bw.work_id ORDER BY bw.avg_rating DESC, bw.title ASC LIMIT 1000"

    '''
    if not query:
            sql += " LIMIT 1000"
    '''

    cursor.execute(sql, params)
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    return books


def fetch_book_details(work_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT bw.title, bw.description, be.isbn13,
               GROUP_CONCAT(DISTINCT a.name SEPARATOR ', ') AS authors,
               GROUP_CONCAT(DISTINCT g.genre_name SEPARATOR ', ') AS genres
        FROM book_work bw
        LEFT JOIN author_work aw ON bw.work_id = aw.work_id
        LEFT JOIN author a ON a.author_id = aw.author_id
        LEFT JOIN category c ON c.work_id = bw.work_id
        LEFT JOIN genre g ON g.genre_id = c.genre_id
        LEFT JOIN book_edition be ON be.work_id = bw.work_id
        WHERE bw.work_id = %s
        GROUP BY bw.work_id
    """, (work_id,))

    book = cursor.fetchone()
    cursor.close()
    conn.close()
    return book


def fetch_user_from_db(username):
    # Fetch user from database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user