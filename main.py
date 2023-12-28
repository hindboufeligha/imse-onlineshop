from flask import Flask, render_template, request, redirect, url_for
import random
import sqlite3
from flask_sqlalchemy import (
    SQLAlchemy,
)  # to define the tables, relationships, and associations in our Online Shop Web Application.
from sqlalchemy import create_engine
from sqlalchemy.sql import func
from sqlalchemy.orm import aliased
from sqlalchemy.orm import Session
from faker import Faker
from faker.providers import (
    BaseProvider,
)  # to create a custom provider for Faker to generate random Image URLs
from datetime import datetime
from lib.init_database_functions import *

app = create_app()


create_database(app)
initialize_tables(app)


@app.route("/hh")
def indexxx():
    # Fetch and display data:
    customers = CustomerTable.query.all()

    # TEST:
    # Output generated products with their subcategories + parent categories.
    # Aliases for self-joins on CategoryTable
    Subcategory = aliased(CategoryTable)
    ParentCategory = aliased(CategoryTable)
    # Query products with their categories and parent categories
    products_with_categories = (
        db.session.query(
            ProductTable,
            CategoryTable.category_name.label("category_name"),
            Subcategory.category_name.label("parent_category_name"),
        )
        .join(CategoryTable, ProductTable.category_id == CategoryTable.category_id)
        .join(
            Subcategory,
            CategoryTable.parent_category_id == Subcategory.category_id,
            isouter=True,
        )
        .all()
    )
    for product, subcategory_name, parent_category_name in products_with_categories:
        print(
            f"Product: {product.p_name}, Subcategory: {subcategory_name}, Parent Category: {parent_category_name}"
        )

    return render_template("index.html", customers=customers)


@app.route("/fill_database", methods=["POST"])
def fill_database():
    initialize_tables(app)
    # Redirect to the index page
    return redirect(url_for("DB_operation"))


# Route to empty the database
@app.route("/empty_database", methods=["POST"])
def empty_database():
    # Delete all data from the customer_table
    db.session.query(CustomerTable).delete()
    db.session.commit()

    # Redirect to the index page
    return redirect(url_for("DB_operation"))


@app.route("/add-review")
def add_review():
    return render_template("add-review.html")


# Route to display login page
@app.route("/login", methods=["GET"])
def show_login():
    return render_template("login.html")


# Route to handle login form submission
@app.route("/login", methods=["POST"])
def login():
    # Retrieve email and password from the form
    email = request.form.get("email")
    password = request.form.get("password")

    # Check the database for the given email and password
    user = CustomerTable.query.filter_by(email=email, password=password).first()

    if user:
        # Successful login, redirect to the index page
        return redirect(url_for("index"))
    else:
        # Invalid credentials, render the login page with an error message
        error_message = "Invalid email or password. Please try again."
        return render_template("login.html", error_message=error_message)


## Cookies --->

## End of Cookies --->


@app.route("/")
def DB_operation():
    return render_template("DB_operation.html")


@app.route("/index")
def index():
    return render_template("index.html")


@app.route("/products")
def products():
    return render_template("products.html")


@app.route("/single-product.html")
def sproduct():
    return render_template("single-product.html")


if __name__ == "__main__":
    app.run(debug=True)
