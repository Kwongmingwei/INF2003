# nosql_service.py
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
import mysql.connector
from pymongo.errors import DuplicateKeyError

client = MongoClient("mongodb://localhost:27017")
db = client["reviews_db"]
reviews = db["reviews"]

# compund key to ensure uniquness
# reviews.create_index([("User_id", 1), ("ISBN13", 1)], unique=True)

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='password',
        database='book_review'
    )

def create_review(user_id, isbn13, rating, summary, text):
    review = {
        "User_id": user_id,
        "ISBN13": isbn13,
        "rating": rating,
        "review_summary": summary,
        "review_text": text,
        "review_date_time": datetime.now()
    }
    try:
        return reviews.insert_one(review)
    except DuplicateKeyError:
         print("User has already reviewed this book.")
         return None


def get_reviews_by_isbn(isbn13):
    review_list = []

    for r in reviews.find({"ISBN13": isbn13}).sort("review_date_time", -1):
        r["_id"] = str(r["_id"])

        # Default fallback
        r["username"] = "Unknown User"

        try:
            user_id = r.get("User_id")
            if user_id:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT username FROM user WHERE user_id = %s", (user_id,))
                result = cursor.fetchone()
                if result:
                    r["username"] = result[0]
                cursor.close()
                conn.close()
        except:
            pass

        review_list.append(r)

    return review_list

def get_review_by_id(review_id):
    try:
        return reviews.find_one({"_id": ObjectId(review_id)})
    except Exception:
        return None

def update_review(review_id, new_summary, new_rating):
    try:
        return reviews.update_one(
            {"_id": ObjectId(review_id)},
            {"$set": {"review_summary": new_summary, "rating": new_rating}}
        )
    except Exception:
        return None

def delete_review(review_id):
    try:
        return reviews.delete_one({"_id": ObjectId(review_id)})
    except Exception:
        return None


def get_aggregate_rating_for_work(list_of_isbns: list):
    """
    Performs a single, efficient aggregation to get the total rating sum and
    review count for all reviews associated with a list of ISBNs.
    Ignores reviews where the rating is not a number/null.

    Args:
        list_of_isbns: A list of ISBN13 strings.

    Returns:
        A dictionary with 'total_rating_sum' and 'total_review_count',
        or None if no valid reviews are found.
    """
    if not list_of_isbns:
        return None

    pipeline = [
        # Match documents for the correct ISBNs AND where rating is a number
        {"$match": {
            "ISBN13": {"$in": list_of_isbns},
            "rating": {"$type": "number"}
        }},
        # Group all valid documents into a single result
        {"$group": {
            "_id": None,
            "total_rating_sum": {"$sum": "$rating"},
            "total_review_count": {"$sum": 1}
        }}
    ]

    try:
        result = list(reviews.aggregate(pipeline))
        if not result:
            return None
        # Return the first (and only) document from the result list
        return result[0]
    except Exception as e:
        print(f"An error occurred during aggregation: {e}")
        return None