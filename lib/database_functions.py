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
