# nosql_service.py
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId

client = MongoClient("mongodb://localhost:27017")
db = client["reviews_db"]
reviews = db["reviews"]

def create_review(user_id, isbn13, rating, summary, text):
    review = {
        "User_id": user_id,
        "ISBN13": isbn13,
        "rating": rating,
        "review_summary": summary,
        "review_text": text,
        "review_date_time": datetime.now()
    }
    return reviews.insert_one(review)

def get_reviews_by_isbn(isbn13):
    if not isbn13:
        return []
    
    # Fetch all reviews with matching ISBN13, newest first
    reviews_cursor = reviews.find({"ISBN13": isbn13}).sort("review_date_time", -1)
    
    # Convert cursor to list and handle datetime formatting
    review_list = []
    for r in reviews_cursor:
        r["_id"] = str(r["_id"])  # convert ObjectId to string if needed
        review_list.append(r)
    return review_list

from bson.objectid import ObjectId

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
