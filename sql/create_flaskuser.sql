-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS book_review;

-- Create the user 'flaskuser' with a password
-- Replace 'password' with a secure password of your choice
CREATE USER IF NOT EXISTS 'flaskuser'@'localhost' IDENTIFIED BY 'password';

-- Grant minimal CRUD privileges (sufficient for SQLAlchemy with transactions)
GRANT SELECT, INSERT, UPDATE, DELETE ON book_review.* TO 'flaskuser'@'localhost';

-- Apply all changes
FLUSH PRIVILEGES;
