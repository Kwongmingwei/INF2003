from flask import Flask, render_template, request

app = Flask(__name__)

# Dummy book data
books = {
    1: {"title": "The Simulated Journey", "author": "Jane Doe", "genre": "Adventure", "isbn": "123-4567890123", "description": "An epic voyage into the unknown."},
    2: {"title": "Romantic Algorithms", "author": "John Smith", "genre": "Romance", "isbn": "234-5678901234", "description": "Love and logic intertwined."},
    3: {"title": "History of Nothing", "author": "Alice Example", "genre": "History", "isbn": "345-6789012345", "description": "A deep dive into forgotten times."}
}

reviews = {
    1: [
        {"user": "Alice", "rating": 5, "comment": "Amazing journey!"},
        {"user": "Bob", "rating": 4, "comment": "Exciting and imaginative."}
    ],
    2: [
        {"user": "Charlie", "rating": 3, "comment": "Interesting concept, but a bit dry."},
        {"user": "Dana", "rating": 4, "comment": "Loved the emotional angle!"}
    ],
    3: [
        {"user": "Eve", "rating": 2, "comment": "Too abstract for my taste."}
    ]
}

@app.route('/')
def index():
    return render_template('index.html', books=books)

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = books.get(book_id)
    book_reviews = reviews.get(book_id, [])
    if not book:
        return "Book not found", 404
    if request.headers.get("Hx-Request") == "true":
        return render_template("partials/book_detail.html", book=book, reviews=book_reviews)
    return render_template("book_detail.html", book=book, reviews=book_reviews)
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
