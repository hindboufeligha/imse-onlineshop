from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    session,
    send_from_directory,
    flash,
)
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
from sqlalchemy.orm.exc import FlushError
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from flask_pymongo import PyMongo
from bson import ObjectId


def addToCart(customer_id, request, db):
    product_id = request.json["product_id"]
    # print("product ID:", product_id)
    size_name = request.json["size_name"]
    # print("size name:", size_name)
    selected_quantity = request.json["selected_quantity"]
    # print("selected quantity: ", selected_quantity)

    # fetch the size id of the selected size:
    size_id = SizeTable.query.filter_by(size_name=size_name).first()

    if size_id is None:
        return jsonify({"error": "Invalid size name"}), 400

    # first, check if the customer has an Active cart or not:
    cart = CartTable.query.filter_by(customer_id=customer_id, status="Active").first()

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


def displayCartItems(customer_id, db):
    # fetch the cart_items associated with this customer:
    # fetch the p_price from ProductTable
    # fetch all the cartitems of the current Active cart (size, quantity)
    # and then calculate the total cost for each size and product
    # first, check if the customer has an Active cart or not:
    cart = CartTable.query.filter_by(customer_id=customer_id, status="Active").first()

    if cart is not None:  # there is an active cart
        # check if the product with the same size is already in the cart for the customer:

        existing_cart_items = CartItemTable.query.filter_by(cart_id=cart.cart_id).all()

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


def displayProducts(request, db):
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


def displayGenderProducts(gender, db):
    products = ProductTable.query.filter_by(p_gender=gender).all()
    return products


def displaySingleProduct(product_id, request, db):
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

    return sizes


def displayPopularProducts(db):
    six_months_ago = datetime.utcnow() - timedelta(days=180)

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
    ).subquery()

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
        .filter(text("rank == 1"))
        .all()
    )

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
        for category_id, product_id, product_name, product_image_url, product_price, total_quantity, cart_item_count, customer_count in popular_products_query
    ]

    return result_data

    # return {'data': result_data}


def fetchCustomerData(customer_id, db):
    customer_data = CustomerTable.query.filter_by(customer_id=customer_id).first()
    return customer_data


def fetchProductData(product_id, db):
    product = ProductTable.query.get(product_id)
    return product


# comment
