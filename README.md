# INF2003 Book Review Platform

A web application for book reviews and ratings using Flask, MariaDB (SQL), and MongoDB (NoSQL).

## Features

- User registration and login
- Browse and search books
- Submit, edit, and delete reviews
- View book details and ratings
- Admin CLI for batch rating population

## Project Structure

- `app.py` — Main Flask application
- `nosql_service.py` — MongoDB review operations
- `sql_service.py` — MariaDB book/user operations
- `templates/` — HTML templates
- `static/` — CSS styles
- `no_sql_db/` — NoSQL data dumps
- `sql/` — SQL schema and scripts

## Prerequisites

- Python 3.11+
- MariaDB/MySQL server
- MongoDB server
- Install dependencies:

## Setup

1. Install Python dependencies

    ```bash
    pip install -r requirements.txt
    ```

2. Set up MariaDB (SQL) database
   - Start your MariaDB/MySQL server.
   - Create a new database (e.g., `book_review`):
   - Run the schema script:
     - Create a user "dev@localhost" with password as "password: `mysql -u <user> -p <database> < sql/create_dev.sql`
     - Populate with sample data: `mysql -u <user> -p <database> < sql/book_review_no_ol_v2.sql`

3. Set up MongoDB (NoSQL) database
   - Start MongoDB and import initial data using mongorestore:
     - Ensure MongoDB is running.
     - Import the reviews dataset: `mongorestore --db reviews_db no_sql_db/reviews_db/`

4. Configure connection settings
   - Edit connection details in `sql_service.py` and `nosql_service.py` as needed.

5. Populate average ratings in SQL from MongoDB
   - After importing the MongoDB dataset, run the Flask CLI command to update average ratings:
     ```bash
     flask populate-ratings
     ```
   - This ensures the SQL database reflects the latest ratings from MongoDB.

## Running the App

   - Start the Flask server 
   - Visit http://localhost:5000 in your browser.
   - Visit http://localhost:5000/db-test to test database connections.
