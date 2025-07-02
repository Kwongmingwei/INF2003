import logging
import re

import mysql.connector
from isbnlib import to_isbn13, is_isbn10, is_isbn13

from nosql_service import get_aggregate_rating_for_work
from utils import log_duration


def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='dev',  # change this
        password='password',  # change this
        database='book_review',
        charset='utf8mb4'
    )


def normalize_isbn(isbn_raw):
    """ Normalize an ISBN string to ISBN-13 format."""
    isbn = re.sub(r'[^0-9X]', '', isbn_raw.upper())  # remove dashes/spaces
    if is_isbn10(isbn):
        return to_isbn13(isbn)
    elif is_isbn13(isbn):
        return isbn
    else:
        return None


def _calculate_and_stage_update(work_id, cursor) -> bool:
    """
    Calculates rating by calling the get_aggregate_rating_for_work from nosql_service.py
    and stages the change in the SQLAlchemy session WITHOUT committing.
    """
    cursor.execute("SELECT * FROM book_work WHERE work_id = %s", (work_id,))
    work_to_update = cursor.fetchone()

    if not work_to_update:
        logging.error(f"No book_work found with work_id: {work_id}")
        return False

    # Get list of all ISBN13 strings associated with work_id
    cursor.execute("SELECT isbn13 FROM book_edition WHERE work_id = %s", (work_id,))
    rows = cursor.fetchall()
    list_of_isbns = [row[0] for row in rows]

    # Call get_aggregate_rating_for_work to get the aggregate stats
    stats = get_aggregate_rating_for_work(list_of_isbns)

    if not stats:
        cursor.execute("UPDATE book_work SET avg_rating = NULL WHERE work_id = %s", (work_id,))
        return True  # Correctly determined there is no rating.

    total_sum = stats.get('total_rating_sum', 0)
    total_count = stats.get('total_review_count', 0)
    avg_rating = total_sum / total_count

    if total_count > 0:
        cursor.execute("UPDATE book_work SET avg_rating = %s WHERE work_id = %s", (avg_rating, work_id,))
    return True


def get_work_id_for_isbn(isbn13: str):
    """
    Finds the work_id associated with a given ISBN13.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if not isbn13:
        return None
    cursor.execute(
        "SELECT bw.work_id FROM book_work bw JOIN book_edition be ON bw.work_id=be.work_id WHERE be.isbn13 = %s",
        (isbn13,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()
    return result.get("work_id") if result else None


def update_work_rating(work_id: int):
    """
    This is our main trigger function. It creates a new session,
    recalculates the average rating for a single work, and commits the change.
    """
    if not work_id:
        logging.warning("update_work_rating called with no work_id.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    conn.start_transaction()

    try:
        if _calculate_and_stage_update(work_id, cursor):
            conn.commit()
            logging.info(f"Successfully updated avg_rating for work_id: {work_id}")
        else:
            conn.rollback()
            logging.info(f"No rating update applied for work_id: {work_id}")
    except Exception as e:
        logging.error(f"Failed to update rating for work_id {work_id}: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


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

@log_duration("fetch_books_from_db(sql)")
def fetch_books_from_db(query=None, field="title", genres=None, year_from=None, year_to=None):
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
        elif field == "isbn":
            normalized = normalize_isbn(query)
            if normalized:
                # If valid isbn13, search for it
                conditions.append("be.isbn13 = %s")
                params.append(normalized)
            else:
                # If invalid, return early
                return []

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
    # print("--- EXECUTING SQL ---")
    # print(sql)
    # print("--- WITH PARAMS ---")
    # print(params)
    # print("--- WITH CON ---")
    # print(conditions)

    cursor.execute(sql, params)
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    return books


def fetch_book_details(work_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT bw.title, bw.description, be.isbn13,MIN(be.cover_id) AS cover_id,
               GROUP_CONCAT(DISTINCT a.name SEPARATOR ', ') AS authors,
               GROUP_CONCAT(DISTINCT g.genre_name SEPARATOR ', ') AS genres,
               GROUP_CONCAT(DISTINCT a.author_id) AS author_ids
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
    if book and book.get("author_ids"):
        book["author_ids"] = [int(aid) for aid in book["author_ids"].split(",") if aid]
    else:
        book["author_ids"] = []
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


def fetch_top_books_by_authors(author_ids, limit=4, work_id=None):
    """
    Returns a list of the top books (by avg_rating DESC, then title ASC) for a list of author_ids.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    placeholders = ','.join(['%s'] * len(author_ids))
    sql = f'''
        SELECT bw.work_id, bw.title, bw.avg_rating, MIN(be.cover_id) AS cover_id
        FROM book_work bw
        JOIN author_work aw ON bw.work_id = aw.work_id
        LEFT JOIN book_edition be ON be.work_id = bw.work_id
        WHERE aw.author_id IN ({placeholders})
    '''
    params = list(author_ids)
    if work_id is not None:
        sql += " AND bw.work_id != %s"
        params.append(work_id)
    sql += '''
        GROUP BY bw.work_id, bw.title, bw.avg_rating
        ORDER BY bw.avg_rating DESC, bw.title ASC
        LIMIT %s
    '''
    params.append(limit)
    cursor.execute(sql, params)
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    return books

def fetch_editions_for_work(work_id):
    """
    Returns a list of all editions for a given work_id, including isbn13, isbn10, publisher_name, and publish_year.
    """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT isbn13, isbn10, publisher_name, publish_year
        FROM book_edition
        WHERE work_id = %s
        ORDER BY publish_year DESC
    """, (work_id,))
    editions = cursor.fetchall()
    cursor.close()
    conn.close()
    return editions
