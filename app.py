from datetime import date, timedelta

import click
from flask import Flask, render_template, request, redirect, url_for, session, flash
from tqdm import tqdm

from nosql_service import *
from sql_service import *
from sql_service import _calculate_and_stage_update

app = Flask(__name__)
app.secret_key = 'KEY'

app.permanent_session_lifetime = timedelta(minutes=30)
app.config['SESSION_PERMANENT'] = False


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
    author_ids = book.get("author_ids", [])
    author_books = []
    if author_ids:
        author_books = fetch_top_books_by_authors(author_ids, limit=4, work_id=book_id)
    if not book:
        return "Book not found", 404
    
    editions = fetch_editions_for_work(book_id)
    

    isbn13 = book.get("isbn13")
    book_reviews = get_reviews_by_isbn(isbn13) if isbn13 else []

    return render_template("book_detail.html", book=book, book_id=book_id, reviews=book_reviews,
                           author_books=author_books,editions=editions)


@app.template_filter('format_datetime')
def format_datetime(value):
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y %I:%M %p")
    return value


@app.route('/book/<int:book_id>/review', methods=['POST'])
def submit_review(book_id):
    if 'user_id' not in session:
        return "Unauthorized", 401

    summary = request.form['summary']
    text = request.form['review_text']
    rating = int(request.form['rating'])
    user_id = session['user_id']

    book = fetch_book_details(book_id)
    isbn13 = book.get("isbn13")

    if not isbn13:
        return "Cannot add review: ISBN13 not found", 400

    existing = reviews.find_one({
        "User_id": user_id,
        "ISBN13": isbn13
    })

    if existing:
        flash("You've already submitted a review for this book.", "warning")
        return redirect(url_for("book_detail", book_id=book_id))
    else:
        # Insert into MongoDB
        create_review(user_id, isbn13, rating, summary, text)

    # Trigger update_work_rating so that avg_rating in mariadb will be updated
    work_id = get_work_id_for_isbn(isbn13)
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
        # TODO SESSION DOES NOT HAVE USER ID AFTER REGISTER
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

    year_from = request.args.get("year_from", "").strip()
    year_to = request.args.get("year_to", "").strip()

    year_from = int(year_from) if year_from else None
    year_to = int(year_to) if year_to else None

    books = fetch_books_from_db(query if query else None, field, genre_list, year_from, year_to)

    if request.headers.get("HX-Request"):
        return render_template("partials/book_list.html", books=books)
    return render_template("index.html", books=books, all_genres=fetch_all_genres(), top_genres=fetch_top_genres())


@app.route('/book/<int:book_id>/review/edit/<review_id>', methods=['POST'])
def edit_review(book_id, review_id):
    if 'user_id' not in session:
        return "Unauthorized", 401

    review = get_review_by_id(review_id)
    if not review:
        return "Review not found", 404

    # Security check: Only the original author can edit
    if str(review.get("User_id")) != str(session['user_id']):
        return "Forbidden", 403

    new_summary = request.form['summary']
    new_text = request.form['review_text']
    new_rating = int(request.form['rating'])

    update_review(review_id, new_summary, new_text, new_rating)

    isbn13 = review.get("ISBN13")
    work_id = get_work_id_for_isbn(isbn13)
    if work_id:
        update_work_rating(work_id)

    return redirect(url_for('book_detail', book_id=book_id))


@app.route('/book/<int:book_id>/review/delete/<review_id>', methods=['POST'])
def delete_review_route(book_id, review_id):
    if 'user_id' not in session:
        return "Unauthorized", 401

    review = get_review_by_id(review_id)
    if not review:
        return "Review not found", 404

    # Ensure only the owner can delete
    if str(review.get("User_id")) != str(session['user_id']):
        return "Forbidden", 403

    # Get the necessary info before deleting the review
    isbn13 = review.get("ISBN13")
    work_id = get_work_id_for_isbn(isbn13)

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
    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch all work_ids
    cursor.execute("SELECT work_id FROM book_work")
    rows = cursor.fetchall()
    work_id_list = [row[0] for row in rows]

    if not work_id_list:
        print("No book works found in the database.")
        cursor.close()
        conn.close()
        return

    success_count = 0
    fail_count = 0
    progress_bar = tqdm(work_id_list, desc="Populating Ratings")

    for i, work_id in enumerate(progress_bar):
        try:
            if _calculate_and_stage_update(work_id, cursor):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logging.error(f"Critical error on work_id {work_id}: {e}")
            conn.rollback()
            fail_count += 1

        if (i + 1) % batch_size == 0 or (i + 1) == len(work_id_list):
            try:
                logging.info(f"Committing batch of {batch_size} items (up to item #{i + 1})...")
                conn.commit()
                logging.info("Batch committed successfully.")
            except Exception as e:
                logging.error(f"Failed to commit batch: {e}")
                conn.rollback()

    print("\n--- Initialization Complete ---")
    print(f"Successfully processed: {success_count}")
    print(f"Failed items: {fail_count}")

    cursor.close()
    conn.close()


if __name__ == '__main__':
    app.run(debug=True)
