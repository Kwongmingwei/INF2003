# nosql_service.py
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
import mysql.connector

client = MongoClient("mongodb://localhost:27017")
db = client["reviews_db"]
reviews = db["reviews"]

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='zenden',
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
    return reviews.insert_one(review)

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

#calculate total rating for a specific ISBN13
def get_total_rating_by_isbn13(isbn13):
    query = [
        { "$match": { "ISBN13": isbn13 } },
        {
            "$group": {
                "_id": None,
                "total_rating": { "$sum": "$rating" }
            }
        }
    ]
    result = list(reviews.aggregate(query))
    return result[0]["total_rating"] if result else 0

#count reviews for a specific ISBN13
def get_review_count_by_isbn13(isbn13):
    query = [
        { "$match": { "ISBN13": isbn13 } },
        {
            "$group": {
                "_id": None,
                "review_count": { "$sum": 1 }
            }
        }
    ]

    # Print all matching review records (to check)
    matching_reviews = reviews.find({ "ISBN13": isbn13 })
    
    print(f"\nBook Reviews for ISBN13: {isbn13}")
    for r in matching_reviews:
        print(f"- Review Summary: {r.get('review_summary')} | Rating: {r.get('rating')}")

    result = list(reviews.aggregate(query))
    return result[0]["review_count"] if result else 0