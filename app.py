from flask import Flask, render_template, request

app = Flask(__name__)

# Dummy book data
books = {
    1: {"title": "The Simulated Journey", "author": "Jane Doe", "genre": "Adventure", "isbn": "123-4567890123", "description": "An epic voyage into the unknown."},
    2: {"title": "Romantic Algorithms", "author": "John Smith", "genre": "Romance", "isbn": "234-5678901234", "description": "Love and logic intertwined."},
    3: {"title": "History of Nothing", "author": "Alice Example", "genre": "History", "isbn": "345-6789012345", "description": "A deep dive into forgotten times."}
}

@app.route('/')
def index():
    return render_template('index.html', books=books)

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    book = books.get(book_id)
    if not book:
        return "Book not found", 404
    if request.headers.get("Hx-Request") == "true":
        return render_template("partials/book_detail.html", book=book)
    return render_template("book_detail.html", book=book)

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

if __name__ == '__main__':
    app.run(debug=True)
