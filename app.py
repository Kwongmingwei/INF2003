

from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'KEY'

# Dummy book data
books = {
    1: {"title": "The Simulated Journey", "author": "Jane Doe", "genre": "Adventure", "isbn": "123-4567890123", "description": "An epic voyage into the unknown."},
    2: {"title": "Romantic Algorithms", "author": "John Smith", "genre": "Romance", "isbn": "234-5678901234", "description": "Love and logic intertwined."},
    3: {"title": "History of Nothing", "author": "Alice Example", "genre": "History", "isbn": "345-6789012345", "description": "A deep dive into forgotten times."}
}

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


@app.route('/')
def index():
    if request.headers.get("Hx-Request") == "true":
        return render_template("partials/book_list.html", books=books)
    return render_template('index.html', books=books)

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = books.get(book_id)
    if not book:
        return "Book not found", 404
    book_reviews = reviews.get(book_id, [])
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
    query = request.args.get("query", "").lower()
    field = request.args.get("searchDropdown", "title")

    if not query:
        filtered = books
    else:
        filtered = {
            id: book for id, book in books.items()
            if query in book.get(field, "").lower()
        }

    if request.headers.get("HX-Request"):
        return render_template("partials/book_list.html", books=filtered)
    return render_template("index.html", books=filtered)

@app.route('/genre/<genre>')
def filter_by_genre(genre):
    filtered = {
        id: book for id, book in books.items()
        if book['genre'].lower() == genre.lower()
    }
    if request.headers.get("HX-Request"):
        return render_template("partials/book_list.html", books=filtered)
    return render_template("index.html", books=filtered)




if __name__ == '__main__':
    app.run(debug=True)
