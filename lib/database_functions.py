from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    json,
    session,
    send_from_directory,
    flash,
    current_app,
)
from sqlalchemy import MetaData
from flask_session import Session
from flask_bcrypt import Bcrypt
from bcrypt import hashpw, gensalt
import bcrypt
from datetime import datetime, timedelta
from sqlalchemy.sql import func
import os
import random
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func, desc, select, text
from lib.init_database_functions import *
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import FlushError
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from flask_pymongo import PyMongo
from bson import ObjectId
import pandas as pd
import numpy as np
from lib.init_database_functions import *
import json
from bson import ObjectId


def convert_to_serializable(obj):
    # Convert non-serializable types to a serializable format:
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, bytes):
        # Convert bytes to a string or other serializable format
        return obj.decode("utf-8")
    elif isinstance(obj, list):
        # Recursively convert elements in lists
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        # Recursively convert values in dictionaries
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    # Add more cases for other non-serializable types as needed

    # If the type is still not serializable, return a placeholder or None
    return obj



def serialize_customer(customer):
    """
    Takes a CustomerTable object and returns a dictionary
    with all the fields that need to be serialized.
    """
    return {
        "customer_id": customer.customer_id,
        "firstname": customer.firstname,
        "familyname": customer.familyname,
        "email": customer.email,
        "phone_no": customer.phone_no,
        "username": customer.username,
        # ... include other fields as necessary
    }



def check_for_tables(db):
    with current_app.app_context():
        meta = db.metadata
        meta.reflect(bind=db.engine)
        tables = meta.tables.keys()
    return tables


def emptyDatabase(app, db):
    with app.app_context():
        db.reflect()
        db.drop_all()
        # db.create_all()


def check_tables_exist(db):
    """Function to check if there are any tables in the SQLAlchemy database."""
    with current_app.app_context():
        metadata = db.MetaData()
        metadata.reflect(bind=db.engine)
        table_names = metadata.tables.keys()
        return len(table_names) > 0


def validate_user_credentials(email, password):
    user = CustomerTable.query.filter_by(email=email).first()
    if user and bcrypt.checkpw(password.encode("utf-8"), user.password):
        return user, True
    else:
        return None, False


def checkExistingUser(email):
    return CustomerTable.query.filter_by(email=email).first() is not None


def add_customer(firstname, familyname, email, phone_no, username, password):
    new_customer = CustomerTable(
        firstname=firstname,
        familyname=familyname,
        email=email,
        phone_no=phone_no,
        username=username,
        password=password,
    )
    db.session.add(new_customer)
    db.session.commit()





def TopProducts(db, mongo_db, db_status, gender):
    if db_status == "SQL":
        # SQL database logic (existing logic)
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        avg_ratings = (
            db.session.query(
                ReviewTable.product_id,
                func.avg(ReviewTable.rating).label("average_rating"),
            )
            .filter(ReviewTable.post_date >= six_months_ago)
            .group_by(ReviewTable.product_id)
            .subquery()
        )

        return (
            db.session.query(ProductTable, avg_ratings.c.average_rating)
            .join(avg_ratings, ProductTable.p_id == avg_ratings.c.product_id)
            .filter(ProductTable.p_gender == gender)
            .order_by(avg_ratings.c.average_rating.desc())
            .limit(5)
            .all()
        )

    elif db_status == "NoSQL":
        # MongoDB logic
        six_months_ago = datetime.utcnow() - timedelta(days=180)

        # MongoDB aggregation pipeline
        pipeline = [
        {"$match": {"post_date": {"$gte": six_months_ago}}},
        {"$group": {
            "_id": "$product_id",
            "average_rating": {"$avg": "$rating"}
        }},
        {"$sort": {"average_rating": -1}},
        {"$limit": 5},
        {"$lookup": {
            "from": "products",
            "localField": "_id",
            "foreignField": "_id",
            "as": "product_details"
        }},
        {"$unwind": "$product_details"},
        {"$match": {"product_details.p_gender": gender}},
        {"$project": {
            "product_id": "$_id",
            "average_rating": 1,
            "product_name": "$product_details.p_name",
            "product_price": "$product_details.p_price",
            "product_image_url": "$product_details.p_image_url"
        }}
    ]

    return list(mongo_db.reviews.aggregate(pipeline))



def userReviews(db, mongo_db, db_status, user_id):
    formatted_reviews = []
    if db_status == "SQL":
        user_data = CustomerTable.query.filter_by(customer_id=user_id).first()
        user_reviews = ReviewTable.query.filter_by(customer_id=user_id).all() if user_data else []

    elif db_status == "NoSQL":
        # Convert user_id to string if it's not already a string
        user_id_str = str(user_id)
        user_data = mongo_db.customers.find_one({"_id": user_id_str})
        user_reviews = list(mongo_db.reviews.find({"customer_id": user_id_str})) if user_data else []

    for review in user_reviews:
        if db_status == "SQL":
            # Format review data from SQL
            formatted_review = {
                'title': review.title,
                'description': review.description,
                'rating': review.rating,
                'post_date': review.post_date.strftime("%Y-%m-%d %H:%M:%S") if review.post_date else None,
                'image_url': review.image_url,
                'ReviewID': review.ReviewID,
                'product_id': review.product_id
            }
        else:
            # Format review data from MongoDB
            # Assuming that product_id is stored directly in the review document
            formatted_review = {
                'title': review.get('title'),
                'description': review.get('description'),
                'rating': review.get('rating'),
                'post_date': review.get('post_date').strftime("%Y-%m-%d %H:%M:%S") if review.get('post_date') else None,
                'image_url': review.get('image_url'),
                'ReviewID': str(review.get('_id')),  # Convert ObjectId to string
                'product_id': str(review.get('product_id'))  # Convert ObjectId to string
            }
        formatted_reviews.append(formatted_review)

    # Convert user_data to a dictionary if it's not None
    user_data_dict = user_data if user_data else None
    return formatted_reviews, user_data_dict




def searchReviews(db, mongo_db, db_status, search_query):
    if db_status == "SQL":
        # SQL database logic
        return ReviewTable.query.filter(ReviewTable.title.like(f"%{search_query}%")).all()

    elif db_status == "NoSQL":
        # MongoDB logic
        return list(mongo_db.reviews.find({"title": {"$regex": search_query, "$options": "i"}}))



def deleteUserReview(db, mongo_db, db_status, review_id):
    if db_status == "SQL":
        # SQL database logic
        review = ReviewTable.query.get(review_id)
        if review:
            db.session.delete(review)
            db.session.commit()
            return 200, "Review deleted successfully"
        else:
            return 404, "Review not found"

    elif db_status == "NoSQL":
        # MongoDB logic
        result = mongo_db.reviews.delete_one({"_id": review_id})
        if result.deleted_count > 0:
            return 200, "Review deleted successfully"
        else:
            return 404, "Review not found"


def userData(db, mongo_db, db_status, user_id):
    if db_status == "SQL":
        # SQL database logic
        return CustomerTable.query.filter_by(customer_id=user_id).first()

    elif db_status == "NoSQL":
        # MongoDB logic
        return mongo_db.customers.find_one({"_id": user_id})


def getProduct(db, mongo_db, db_status, product_id):
    if db_status == "SQL":
        # SQL database logic
        return ProductTable.query.get(product_id)

    elif db_status == "NoSQL":
        # MongoDB logic
        return mongo_db.products.find_one({"_id": product_id})


def getCreateReview(db, mongo_db, db_status, user_id, product_id, title=None, description=None, rating=None, get_only=False):
    if db_status == "SQL":
        # SQL database logic
        review = ReviewTable.query.filter_by(customer_id=user_id, product_id=product_id).first()
        if get_only:
            return review

        if review:
            review.title = title
            review.description = description
            review.rating = rating
            review.post_date = datetime.utcnow()
        else:
            new_review = ReviewTable(
                title=title,
                description=description,
                rating=rating,
                post_date=datetime.utcnow(),
                customer_id=user_id,
                product_id=product_id,
            )
            db.session.add(new_review)

        db.session.commit()

    elif db_status == "NoSQL":
        # MongoDB logic
        review = mongo_db.reviews.find_one({"customer_id": user_id, "product_id": product_id})
        if get_only:
            return review

        if review:
            mongo_db.reviews.update_one(
                {"_id": review['_id']},
                {"$set": {
                    "title": title,
                    "description": description,
                    "rating": rating,
                    "post_date": datetime.utcnow()
                }}
            )
        else:
            new_review = {
                "title": title,
                "description": description,
                "rating": rating,
                "post_date": datetime.utcnow(),
                "customer_id": user_id,
                "product_id": product_id
            }
            mongo_db.reviews.insert_one(new_review)


def submitUpdateReview(db, mongo_db, db_status, user_id, product_id, title, description, rating, image_url):
    if db_status == "SQL":
        # SQL database logic
        existing_review = ReviewTable.query.filter_by(
            customer_id=user_id, product_id=product_id
        ).first()

        if existing_review:
            # Update the existing review
            existing_review.title = title
            existing_review.description = description
            existing_review.rating = rating
            existing_review.image_url = image_url
        else:
            # Create a new review
            new_review = ReviewTable(
                title=title,
                description=description,
                rating=rating,
                image_url=image_url,
                customer_id=user_id,
                product_id=product_id,
            )
            db.session.add(new_review)

        db.session.commit()

    elif db_status == "NoSQL":
        # MongoDB logic
        existing_review = mongo_db.reviews.find_one({
            "customer_id": user_id, 
            "product_id": product_id
        })

        if existing_review:
            # Update the existing review
            mongo_db.reviews.update_one(
                {"_id": existing_review['_id']},
                {"$set": {
                    "title": title,
                    "description": description,
                    "rating": rating,
                    "image_url": image_url
                }}
            )
        else:
            # Create a new review
            new_review = {
                "title": title,
                "description": description,
                "rating": rating,
                "image_url": image_url,
                "customer_id": user_id,
                "product_id": product_id,
                "post_date": datetime.utcnow()
            }
            mongo_db.reviews.insert_one(new_review)



def associatedProducts(db, mongo_db, db_status, user_id):
    if db_status == "SQL":
        # SQL database logic
        associated_product_ids = (
            db.session.query(customer_product_association.c.productID)
            .filter(customer_product_association.c.customerID == user_id)
            .all()
        )
        product_ids = [pid[0] for pid in associated_product_ids]
        return ProductTable.query.filter(ProductTable.p_id.in_(product_ids)).all()

    elif db_status == "NoSQL":
        # MongoDB logic
        associated_products = mongo_db.customer_product_association.find({"customerID": user_id})
        product_ids = [ap['productID'] for ap in associated_products]
        return list(mongo_db.products.find({"_id": {"$in": product_ids}}))



def searchProducts(db, mongo_db, db_status, search_query):
    if db_status == "SQL":
        # SQL database logic
        return ProductTable.query.filter(ProductTable.p_name.like(f"%{search_query}%")).all()

    elif db_status == "NoSQL":
        # MongoDB logic
        return list(mongo_db.products.find({"p_name": {"$regex": search_query, "$options": "i"}}))




# DONE
def addToCart(customer_id, request, db, mongo_db, db_status):
    product_id = request.json["product_id"]
    # print(product_id)
    size_name = request.json["size_name"]
    # print("size name:", size_name)
    selected_quantity = request.json["selected_quantity"]

    # tables = check_for_tables(db)
    # if tables:

    if db_status == "SQL":
        # fetch the size id of the selected size:
        size_id = SizeTable.query.filter_by(size_name=size_name).first()

        if size_id is None:
            return jsonify({"error": "Invalid size name"}), 400

        # first, check if the customer has an Active cart or not:
        cart = CartTable.query.filter_by(
            customer_id=customer_id, status="Active"
        ).first()

        if cart is None:  # no active cart
            # then we create one:
            cart = CartTable(
                customer_id=customer_id,
                status="Active",
                creation_date=datetime.utcnow(),
            )
            db.session.add(cart)
            db.session.commit()

        # check if the product with the same size is already in the cart for the customer:
        existing_cart_item = CartItemTable.query.filter_by(
            cart_id=cart.cart_id, size=size_name, product_id=product_id
        ).first()

        if existing_cart_item:
            # the product is already in the cart, then update the quantity:
            existing_cart_item.quantity += selected_quantity

        else:
            # if not then add the item and update the db (CartItemTable)
            new_cart_item = CartItemTable(
                cart_id=cart.cart_id,
                product_id=product_id,
                size=size_name,
                quantity=selected_quantity,
            )

            db.session.add(new_cart_item)

        db.session.commit()

    else:
        print("We are in MongoDB. addToCart")
        cart = mongo_db.cart.find_one({"customer_id": customer_id, "status": "Active"})
        if cart is None:
            cart = {
                "_id": 1,
                "status": "Active",
                "creation_date": datetime.utcnow(),
                "customer_id": customer_id,
                "cart_items": [],
            }

            cart_id = 1
        else:
            cart_id = cart["_id"]

        # Check if the product and size already exist in the cart col:
        existing_item = next(
            (
                cart_item
                for cart_item in cart["cart_items"]
                if cart_item["product_id"] == product_id
                and cart_item["size"] == size_name
            ),
            None,
        )

        # Check if the product and size already exist in the cartitem col:
        existing_cartitem = mongo_db.cartitem.find_one(
            {
                "cart_id": cart_id,
                "product_id": product_id,
                "size": size_name,
            }
        )

        if existing_item and existing_cartitem:
            # If the same product and size already exist in cart and cartitem collections, just update the quantity:
            existing_item["quantity"] += selected_quantity
            existing_cartitem["quantity"] += selected_quantity

            # Update the cartitem in the database:
            mongo_db.cartitem.update_one(
                {
                    "cart_id": cart_id,
                    "product_id": product_id,
                    "size": size_name,
                },
                {"$set": existing_cartitem},
                upsert=True,
            )

        # add it as a new cart_item:
        else:
            print("you are in else!")
            # Get the next available _id for the cart item:
            # If not, add it as a new cart_item:
            new_cart_item = {
                "size": size_name,
                "quantity": selected_quantity,
                "product_id": product_id,
            }
            cart["cart_items"].append(new_cart_item)
            print(new_cart_item)

            # Now, Update the cartitem collectiın in the database, by adding/updating the new cartitem document:
            # Get the max existing cart item _id:
            # Find the last cart item in the cart_items collection
            last_cart_item = mongo_db.cartitem.find_one(sort=[("_id", -1)])

            # Get the last _id and increment it by 1:
            next_id = last_cart_item["_id"] + 1 if last_cart_item else 1

            # Create a new cart item document
            new_cart_item = {
                "_id": next_id,
                "size": size_name,
                "quantity": selected_quantity,
                "cart_id": cart_id,
                "product_id": product_id,
            }

        # Update the cart in the database:
        mongo_db.cart.update_one(
            {"customer_id": customer_id, "status": "Active"},
            {"$set": cart},
            upsert=True,
        )

        # Insert the new cart item into the cart_items collection
        mongo_db.cartitem.insert_one(new_cart_item)


# DONE
def displayCartItems(customer_id, db, mongo_db, db_status):
    # fetch the cart_items associated with this customer: and then calculate the total cost for each size and product
    # tables = check_for_tables(db)
    # if tables:

    if db_status == "NoSQL":
        cart = mongo_db.cart.find_one({"customer_id": customer_id, "status": "Active"})
        if cart:
            cart_items = cart.get("cart_items", [])
            # will contain, the size, quantity and product_id but you need also to display the product name and price
            return cart_items
            # return jsonify({"cart_items": cart_items})

        else:
            return cart_items
            # return jsonify({"message": "No active cart found for the user"})

    else:
        # first, check if the customer has an Active cart or not:
        cart = CartTable.query.filter_by(
            customer_id=customer_id, status="Active"
        ).first()

        if cart is not None:  # there is an active cart
            # check if the product with the same size is already in the cart for the customer:

            existing_cart_items = CartItemTable.query.filter_by(
                cart_id=cart.cart_id
            ).all()
            cart_items = (
                db.session.query(
                    ProductTable.p_id,
                    ProductTable.p_name,
                    ProductTable.p_price,
                    CartItemTable.size,
                    CartItemTable.quantity,
                )
                .join(CartItemTable, CartItemTable.product_id == ProductTable.p_id)
                .join(CartTable, CartTable.cart_id == CartItemTable.cart_id)
                .join(
                    CustomerTable,
                    CustomerTable.customer_id == CartTable.customer_id,
                )
                .filter(
                    CustomerTable.customer_id == customer_id,
                    CartTable.status == "Active",
                )
            )
            # Convert the query result to a list of dictionaries
            cart_items_quantity_price = [
                {
                    "p_id": item.p_id,
                    "p_name": item.p_name,
                    "size_name": item.size,
                    "quantity": item.quantity,
                    "p_price": float(item.p_price),  # Convert to float if needed
                }
                for item in cart_items
            ]

        else:  # if the customer does not have any active cart
            cart_items = (
                db.session.query(
                    ProductTable.p_id,
                    ProductTable.p_name,
                    ProductTable.p_price,
                    CartItemTable.size,
                    CartItemTable.quantity,
                )
                .join(CartItemTable, CartItemTable.product_id == ProductTable.p_id)
                .join(CartTable, CartTable.cart_id == CartItemTable.cart_id)
                .join(
                    CustomerTable,
                    CustomerTable.customer_id == CartTable.customer_id,
                )
                .filter(
                    CustomerTable.customer_id == customer_id,
                    CartTable.status == "Active",
                )
            )

        # Render the products page with the user's data and empty cart_items:
        return cart_items


def displayProducts(request, db, mongo_db):
    tables = check_for_tables(db)

    if tables:
        category_name = request.args.get("category_name")
        parent_category_id = request.args.get("parent_category_id")
        p_gender = request.args.get("p_gender")

        # Fetch products based on category_name, parent_category_id, and gender
        products_with_categories = (
            db.session.query(ProductTable)
            .join(CategoryTable, ProductTable.category_id == CategoryTable.category_id)
            .filter(
                CategoryTable.category_name == category_name,
                ProductTable.p_gender == p_gender,
            )
            .all()
        )

        return products_with_categories

    else:
        products_cursor = mongo_db["product"].find()
        # Convert cursor to list
        products = list(products_cursor)
        return products


# DONE
def displayGenderProducts(gender, db, mongo_db, db_status):
    # tables = check_for_tables(db)
    # if tables:

    if db_status == "NoSQL":
        print("We are in MongoDB.")  # CHECK
        print(gender)
        # Find all products with the specified gender
        products_cursor = mongo_db.product.find({"p_gender": gender})
        # Convert cursor to list
        products = list(products_cursor)
        print(products)

        return products

    else:
        print("We are in SQL db.")  # CHECK
        products = ProductTable.query.filter_by(p_gender=gender).all()
        print(products)
        return products


# DONE
def displaySingleProduct(product_id, request, db, mongo_db, db_status):
    if db_status == "NoSQL":
        print("We are in MongoDB. displaySingleProduct")  # CHECK
        product_id = int(product_id)
        product_data = mongo_db.product.find_one({"_id": product_id})
        if product_data:
            sizes = product_data.get("sizes", [])
            print(sizes)
            print(type(sizes))
            return sizes
        else:
            return None

    else:
        print("We are in SQL db.")  # CHECK
        # Fetch sizes and quantities based on the product_id from SizeTable and product_size_association join table
        sizes_quantities = (
            db.session.query(SizeTable.size_name, product_size_association.c.quantity)
            .join(product_size_association)
            .filter(product_size_association.c.p_id == product_id)
            .all()
        )
        sizes = [
            {"name": size, "quantity": quantity} for size, quantity in sizes_quantities
        ]
        print(sizes)
        print(type(sizes))
        return sizes


def displayPopularProducts(db, mongo_db, db_status):  # user_id is stored in the session
    six_months_ago = datetime.utcnow() - timedelta(days=180)

    # tables = check_for_tables(db)
    # if tables:

    if db_status == "SQL":
        product_alias = aliased(ProductTable)
        cart_item_alias = aliased(CartItemTable)
        cart_alias = aliased(CartTable)
        # Construct a CTE with the row number
        new_session = Session()
        subquery = (
            db.session.query(
                ProductTable.category_id,
                ProductTable.p_id,
                ProductTable.p_name,
                ProductTable.p_image_url,
                ProductTable.p_price,
                func.sum(CartItemTable.quantity).label("total_quantity"),
                func.count(CartItemTable.cart_item_id).label("cart_item_count"),
                func.count(CartTable.customer_id.distinct()).label("customer_count"),
                func.row_number()
                .over(
                    partition_by=ProductTable.category_id,
                    order_by=func.count(CartItemTable.quantity).desc(),
                )
                .label("rank"),
            )
            .join(CartItemTable, ProductTable.p_id == CartItemTable.product_id)
            .join(CartTable, CartItemTable.cart_id == CartTable.cart_id)
            .filter(CartTable.creation_date >= six_months_ago)
            .group_by(ProductTable.category_id, ProductTable.p_id)
            .cte()
        )

        # Use the CTE in the outer query to select top-ranked rows
        popular_products_query = (
            db.session.query(
                subquery.c.category_id,
                subquery.c.p_id,
                subquery.c.p_name,
                subquery.c.p_image_url,
                subquery.c.p_price,
                subquery.c.total_quantity,
                subquery.c.cart_item_count,
                subquery.c.customer_count,
            )
            .filter(text("rank = 1"))
            .all()
        )

        new_session.close()
        # Process the results as needed, e.g., return them as JSON
        result_data = [
            {
                "category_id": category_id,
                "product_id": product_id,
                "product_name": product_name,
                "product_image_url": product_image_url,
                "product_price": product_price,
                "total_quantity": total_quantity,
                "cart_item_count": cart_item_count,
                "customer_count": customer_count,
            }
            for (
                category_id,
                product_id,
                product_name,
                product_image_url,
                product_price,
                total_quantity,
                cart_item_count,
                customer_count,
            ) in popular_products_query
        ]

        print(result_data)

        return result_data

    # return {'data': result_data}

    else:
        # Step 2: Aggregate cart items within the last 6 months

        # Aggregation pipeline:
        pipeline = [
            {
                "$lookup": {
                    "from": "product",
                    "localField": "product_id",
                    "foreignField": "_id",
                    "as": "product_info",
                }
            },
            {"$unwind": "$product_info"},
            {
                "$lookup": {
                    "from": "cart",
                    "localField": "cart_id",
                    "foreignField": "_id",
                    "as": "cart_info",
                }
            },
            {"$unwind": "$cart_info"},
            {"$match": {"cart_info.creation_date": {"$gte": six_months_ago}}},
            {
                "$group": {
                    "_id": {
                        "category_id": "$product_info.category_id",
                        "product_id": "$product_id",
                        "product_name": "$product_info.p_name",
                        "product_image_url": "$product_info.p_image_url",
                        "product_price": "$product_info.p_price",
                    },
                    "total_quantity": {"$sum": "$quantity"},
                    "unique_customers": {"$addToSet": "$cart_info.customer_id"},
                }
            },
            {"$sort": {"total_quantity": -1}},
            {
                "$group": {
                    "_id": "$_id.category_id",
                    "top_popular_product": {
                        "$first": {
                            "category_id": "$_id.category_id",
                            "product_id": "$_id.product_id",
                            "product_name": "$_id.product_name",
                            "product_image_url": "$_id.product_image_url",
                            "product_price": "$_id.product_price",
                            "total_quantity": "$total_quantity",
                            "customer_count": {"$size": "$unique_customers"},
                        }
                    },
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "category_id": "$top_popular_product.category_id",
                    "product_id": "$top_popular_product.product_id",
                    "product_name": "$top_popular_product.product_name",
                    "product_image_url": "$top_popular_product.product_image_url",
                    "product_price": "$top_popular_product.product_price",
                    "total_quantity": "$top_popular_product.total_quantity",
                    "customer_count": "$top_popular_product.customer_count",
                }
            },
        ]

        # Execute the aggregation pipeline
        result = list(mongo_db.cartitem.aggregate(pipeline))
        print(result)

        # Optionally, you can further process the result based on your needs
        return result


# DONE
def fetchCustomerData(customer_id, db, mongo_db, db_status):
    # tables = check_for_tables(db)

    # Check if there are any tables
    if db_status == "NoSQL":
        print("We are in MongoDB.")  # CHECK
        customer_data = mongo_db.customer.find_one({"_id": customer_id})
        # customer_data = mongo_db["customer"].find_one({"_id": customer_id})
        if customer_data:
            customer_data = convert_to_serializable(
                customer_data
            )  # Convert to serializabler
            return customer_data

        else:
            return None

    else:
        print("We are in SQL db.")  # CHECK
        customer_data = CustomerTable.query.filter_by(customer_id=customer_id).first()
        customer_data = (
            json.dumps(
                customer_data,
                default=lambda x: x.as_dict() if isinstance(x, CustomerTable) else None,
            )
            if customer_data
            else None
        )
        return customer_data


# DONE
def fetchProductData(product_id, db, mongo_db, db_status):
    # tables = check_for_tables(db)
    # if tables:

    if db_status == "NoSQL":
        print("We are in MongoDB. fetchProductData")  # CHECK
        product_id = int(product_id)
        product_data = mongo_db["product"].find_one({"_id": product_id})
        if product_data:
            return product_data
        else:
            return None

    else:
        print("We are in SQL db.")  # CHECK
        product_data = ProductTable.query.get(product_id)
        if product_data:
            return product_data

        else:
            return None


from datetime import datetime, timedelta
from bson import ObjectId


def find_popular_products_last_6_months():
    # Calculate the start date for the last 6 months
    six_months_ago = datetime.utcnow() - timedelta(days=180)
