import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import date
from nosql_service import create_review, get_reviews_by_isbn, update_review, get_review_by_id, delete_review
import click
import logging
from tqdm import tqdm
from sql_service import Session, BookWork, get_work_id_for_isbn, update_work_rating, _calculate_and_stage_update


def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',  # change this
        password='zenden',  # change this
        database='book_review',
        charset='utf8mb4'
    )


app = Flask(__name__)
app.secret_key = 'KEY'

users = {
    "john": {"password": "1234"},
    "alice": {"password": "abcd"}
}


# reviews = {
#     1: [
#         {"user": "john", "rating": 5, "comment": "Amazing journey!"},
#         {"user": "alice", "rating": 4, "comment": "Exciting and imaginative."}
#     ],
#     3: [
#         {"user": "alice", "rating": 2, "comment": "Too abstract for my taste."}
#     ]
# }


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


# db connection test
# flask run
# http://localhost:5000/db-test
@app.route('/db-test')
def db_test():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE();")
        current_db = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"✅ Successfully connected to database: {current_db[0]}"
    except Exception as e:
        return f"❌ Database connection failed: {e}"


def fetch_books_from_db(query=None, field="title", genres=None):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT bw.work_id, bw.title, GROUP_CONCAT(DISTINCT a.name SEPARATOR ', ') AS authors, GROUP_CONCAT(DISTINCT g.genre_name SEPARATOR ', ') AS genres
        FROM book_work bw
        LEFT JOIN author_work aw ON bw.work_id = aw.work_id
        LEFT JOIN author a ON a.author_id = aw.author_id
        LEFT JOIN category c ON c.work_id = bw.work_id
        LEFT JOIN genre g ON g.genre_id = c.genre_id
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

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " GROUP BY bw.work_id LIMIT 1000"

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


@app.route('/')
def index():
    books = fetch_books_from_db()
    all_genres = fetch_all_genres()
    top_genres = fetch_top_genres()
    if request.headers.get("Hx-Request") == "true":
        return render_template("partials/book_list.html", books=books)
    return render_template('index.html', books=books, all_genres=all_genres, top_genres=top_genres)


@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = fetch_book_details(book_id)
    if not book:
        return "Book not found", 404

    isbn13 = book.get("isbn13")
    book_reviews = get_reviews_by_isbn(isbn13) if isbn13 else []

    return render_template("book_detail.html", book=book, book_id=book_id, reviews=book_reviews)


@app.route('/book/<int:book_id>/review', methods=['POST'])
def submit_review(book_id):
    if 'username' not in session:
        return "Unauthorized", 401

    comment = request.form['comment']
    rating = int(request.form['rating'])
    username = session['username']

    book = fetch_book_details(book_id)
    isbn13 = book.get("isbn13")

    if not isbn13:
        return "Cannot add review: ISBN13 not found", 400

    # Insert into MongoDB
    create_review(username, isbn13, rating, comment, comment)

    # Trigger update_work_rating so that avg_rating in mariadb will be updated
    with Session() as db_session:
        work_id = get_work_id_for_isbn(db_session, isbn13)
    if work_id:
        update_work_rating(work_id)

    return redirect(url_for('book_detail', book_id=book_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = fetch_user_from_db(username)

        if user and user['password'] == password:
            session['username'] = user['username']
            session['user_id'] = user['user_id']
            return redirect(url_for('index'))
        return render_template("login.html", error="Invalid credentials")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        datejoined = date.today().strftime('%Y-%m-%d')

        existing_user = fetch_user_from_db(username)
        if existing_user:
            return render_template("register.html", error="Username already taken")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return render_template("register.html", error="Email already taken")

        cursor.execute("""
            INSERT INTO user (username, password, email, date_joined)
            VALUES (%s, %s, %s, %s)
        """, (username, password, email, datejoined))
        conn.commit()
        cursor.close()
        conn.close()

        session['username'] = username
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.clear()
    return redirect(url_for('index'))


@app.route('/search')
def search():
    query = request.args.get("query", "").strip()
    field = request.args.get("searchDropdown", "title")
    genres_str = request.args.get("genres", "")
    genre_list = genres_str.split(",") if genres_str else []

    books = fetch_books_from_db(query if query else None, field, genre_list)

    if request.headers.get("HX-Request"):
        return render_template("partials/book_list.html", books=books)
    return render_template("index.html", books=books, all_genres=fetch_all_genres(), top_genres=fetch_top_genres())


@app.route('/book/<int:book_id>/review/edit/<review_id>', methods=['GET', 'POST'])
def edit_review(book_id, review_id):
    review = get_review_by_id(review_id)
    if not review:
        return "Review not found", 404

    if request.method == 'POST':
        new_summary = request.form['summary']
        new_rating = int(request.form['rating'])

        update_review(review_id, new_summary, new_rating)

        # Trigger update_work_rating so that avg_rating in mariadb will be updated
        isbn13 = review.get("ISBN13")
        with Session() as db_session:
            work_id = get_work_id_for_isbn(db_session, isbn13)
        if work_id:
            update_work_rating(work_id)

        return redirect(url_for('book_detail', book_id=book_id))

    return render_template('edit_review.html', review=review, book_id=book_id)


@app.route('/book/<int:book_id>/review/delete/<review_id>', methods=['POST'])
def delete_review_route(book_id, review_id):
    if 'username' not in session:
        return "Unauthorized", 401

    review = get_review_by_id(review_id)
    if not review:
        return "Review not found", 404

    if review['User_id'] != session['user_id']:
        return "Forbidden", 403

    # Get the necessary info before deleting the review
    isbn13 = review.get("ISBN13")
    with Session() as db_session:
        work_id = get_work_id_for_isbn(db_session, isbn13)

    # Delete review from MongoDB
    delete_review(review_id)

    # Trigger update_work_rating so that avg_rating in mariadb will be updated
    if work_id:
        update_work_rating(work_id)

    return redirect(url_for('book_detail', book_id=book_id))


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@app.cli.command("populate-ratings")
@click.option('--batch-size', default=500, help='Number of records to process before committing.')
def populate_ratings_command(batch_size):
    """
    Calculates and populates the avg_rating for all book_works in the database.
    """
    avg_rating_update_session = Session()

    work_ids_to_process = avg_rating_update_session.query(BookWork.work_id).all()

    if not work_ids_to_process:
        print("No book works found in the database.")
        avg_rating_update_session.close()
        return

    work_id_list: list[int] = [item[0] for item in work_ids_to_process]
    progress_bar = tqdm(work_id_list, desc="Populating Ratings")

    success_count = 0
    fail_count = 0

    for i, work_id in enumerate(progress_bar):
        try:
            if _calculate_and_stage_update(work_id, avg_rating_update_session):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logging.error(f"A critical error occurred for work_id {work_id}: {e}")
            fail_count += 1
            avg_rating_update_session.rollback()  # Rollback on critical error for an item

        # Commit every batches_size, default is 500
        if (i + 1) % batch_size == 0 or (i + 1) == len(work_id_list):
            try:
                logging.info(f"Committing batch of {batch_size} items (up to item #{i + 1})...")
                avg_rating_update_session.commit()
                logging.info("Batch committed successfully.")
            except Exception as e:
                logging.error(f"Failed to commit batch: {e}")
                avg_rating_update_session.rollback()

    print("\n--- Initialization Complete ---")
    print(f"Successfully processed: {success_count}")
    print(f"Failed items: {fail_count}")

    avg_rating_update_session.close()


if __name__ == '__main__':
    app.run(debug=True)