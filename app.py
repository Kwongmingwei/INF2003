
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, session


def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root', #change this
        password='mingwei', #change this
        database='book_review',
        charset='utf8mb4'
    )

app = Flask(__name__)
app.secret_key = 'KEY'

'''
books = {
    1: {"title": "The Simulated Journey", "author": "Jane Doe", "genre": "Adventure", "isbn": "123-4567890123", "description": "An epic voyage into the unknown."},
    2: {"title": "Romantic Algorithms", "author": "John Smith", "genre": "Romance", "isbn": "234-5678901234", "description": "Love and logic intertwined."},
    3: {"title": "History of Nothing", "author": "Alice Example", "genre": "History", "isbn": "345-6789012345", "description": "A deep dive into forgotten times."}
}
'''
# Dummy book data


users = {
    "john": {"password": "1234"},
    "alice": {"password": "abcd"}
}


reviews = {
    1: [
        {"user": "john", "rating": 5, "comment": "Amazing journey!"},
        {"user": "alice", "rating": 4, "comment": "Exciting and imaginative."}
    ],
    3: [
        {"user": "alice", "rating": 2, "comment": "Too abstract for my taste."}
    ]
}

#db connection test
#flask run
#http://localhost:5000/db-test
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


def fetch_books_from_db(query=None, field="title"):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT bw.work_id, bw.title, GROUP_CONCAT(DISTINCT a.name SEPARATOR ', ') AS authors, GROUP_CONCAT(DISTINCT g.genre_name SEPARATOR ', ') AS genres
        FROM book_work bw
        LEFT JOIN author_work aw ON bw.work_id = aw.work_id_fk
        LEFT JOIN author a ON a.author_id = aw.author_id_fk
        LEFT JOIN category c ON c.work_id_fk = bw.work_id
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
        SELECT bw.title, bw.description, GROUP_CONCAT(DISTINCT a.name SEPARATOR ', ') AS authors, GROUP_CONCAT(DISTINCT g.genre_name SEPARATOR ', ') AS genres
        FROM book_work bw
        LEFT JOIN author_work aw ON bw.work_id = aw.work_id_fk
        LEFT JOIN author a ON a.author_id = aw.author_id_fk
        LEFT JOIN category c ON c.work_id_fk = bw.work_id
        LEFT JOIN genre g ON g.genre_id = c.genre_id
        WHERE bw.work_id = %s
        GROUP BY bw.work_id
    """, (work_id,))
    book = cursor.fetchone()
    cursor.close()
    conn.close()
    return book


@app.route('/')
def index():
    books = fetch_books_from_db()
    if request.headers.get("Hx-Request") == "true":
        return render_template("partials/book_list.html", books=books)
    return render_template('index.html', books=books)

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = fetch_book_details(book_id)
    if not book:
        return "Book not found", 404
    book_reviews = reviews.get(book_id, [])  # still dummy for now
    return render_template("book_detail.html", book=book, book_id=book_id, reviews=book_reviews)

@app.route('/book/<int:book_id>/review', methods=['POST'])
def submit_review(book_id):
    if 'username' not in session:
        return "Unauthorized", 401

    comment = request.form['comment']
    rating = request.form['rating']
    username = session['username']

    if book_id not in reviews:
        reviews[book_id] = []

    reviews[book_id].append({
        "user": username,
        "comment": comment,
        "rating": rating
    })

    return redirect(url_for('book_detail', book_id=book_id))


'''
@app.route('/search')
def search():
    query = request.args.get("query", "").lower()
    field = request.args.get("searchDropdown", "title")

    if not query:
        filtered = books
    else:
        filtered = {
            id: book for id, book in books.items()
            if query in book.get(field, "").lower()
        }

    return render_template("partials/book_list.html", books=filtered)
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('index'))
        return "Invalid credentials", 401
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/search')
def search():
    query = request.args.get("query", "").strip()
    field = request.args.get("searchDropdown", "title")

    if not query:
        books = fetch_books_from_db()
    else:
        books = fetch_books_from_db(query, field)

    if request.headers.get("HX-Request"):
        return render_template("partials/book_list.html", books=books)
    return render_template("index.html", books=books)



if __name__ == '__main__':
    app.run(debug=True)
