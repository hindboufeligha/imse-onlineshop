from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    jsonify,
    session,
)
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)

import os
import random
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from lib.init_database_functions import *


app = Flask(__name__, static_folder="assets", template_folder="templates")
app.config["SECRET_KEY"] = os.urandom(24)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///onlineshop_.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["UPLOAD_FOLDER"] = "assets/images"


# Explicitly set the template folder
# app.template_folder = "templates"

db.init_app(app)


# Count the number of records in the CategoryTable
def is_category_table_empty():
    # Count the number of records in the CategoryTable
    count = db.session.query(CategoryTable).count()
    # Check if the count is zero
    return count == 0


@app.route("/hh")
def indexxx():
    customers = db.session.query(CustomerTable).all()
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
        .join(
            CategoryTable,
            ProductTable.category_id == db.CategoryTable.category_id,
        )
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
    count = is_category_table_empty()
    initialize_tables(db, count)
    # Stay at the same page
    return redirect(url_for("DB_operation"))


# Route to empty the database
@app.route("/empty_database", methods=["POST"])
def empty_database():
    # Drop and recreate all tables:
    with app.app_context():
        db.reflect()
        db.drop_all()
        db.create_all()

    # Stay at the same page:
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
    # Retrieve email and password from the form:
    email = request.form.get("email")
    password = request.form.get("password")

    # Check the database for the given email and password:
    customer = CustomerTable.query.filter_by(email=email, password=password).first()

    if customer:
        # Successful login, store the current customer's ID using sessions:
        session["user_id"] = customer.customer_id
        # To retrieve the user in subsequent requests:
        customerID = session.get("user_id")
        # redirect to the index page:
        return redirect(url_for("index", customer=customer))
    else:
        # Invalid credentials, render the login page with an error message
        error_message = "Invalid email or password. Please try again."
        return render_template("login.html", error_message=error_message)


## Cookies --->

## End of Cookies --->


@app.route("/")
def DB_operation():
    return render_template("DB_operation.html")


## Uploading images into product table --->
@app.route("/upload", methods=["GET", "POST"])
def upload_product():
    if request.method == "POST":
        # Get form data
        product_name = request.form.get("product_name")
        description = request.form.get("description")
        price = request.form.get("price")
        gender = request.form.get("gender")
        size_variation = "size_variation" in request.form
        quantity = request.form.get("quantity")
        subcategory_id = request.form.get("subcategory")

        # Get uploaded file
        image_file = request.files["image"]

        # Save the file to the server
        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"], secure_filename(image_file.filename)
        )
        image_file.save(file_path)

        # Check if the subcategory exists
        subcategory = CategoryTable.query.get(subcategory_id)
        if not subcategory:
            return "Invalid subcategory!"

        # Perform database insertion using the form data and file path
        new_product = ProductTable(
            p_name=product_name,
            p_description=description,
            p_price=price,
            p_gender=gender,
            p_size_variation=size_variation,
            category_id=subcategory_id,
            p_image_url=file_path,  # Use file path instead of URL if you're storing it locally
            p_quantity=quantity,
        )
        db.session.add(new_product)
        db.session.commit()

        return "Product uploaded successfully!"

    # Fetch subcategories for the form
    subcategories = CategoryTable.query.all()

    return render_template("img.html", subcategories=subcategories)


## End uploading images --->


@app.route("/index")
def index():
    # Render the dashboard with user-specific information
    return render_template("index.html")


##########


@app.route("/psubcategory")
def psubcategory():
    p_gender = request.args.get("p_gender")
    return render_template("p-subcategory.html", p_gender=p_gender)


@app.route("/products")
def products():
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

    return render_template(
        "products.html",
        products_with_categories=products_with_categories,
        category_name=category_name,
        p_gender=p_gender,
    )


### Display Products based on the gender in products.html ###
# from index, when the user clicks on discover --> depends on the gender --> will be redirected to this page products.html
@app.route("/products/<gender>")
def display_products(gender):
    products = ProductTable.query.filter_by(p_gender=gender).all()
    return render_template("products.html", products=products, p_gender=gender)


### END ###


### Rout to display the selected Product details on single-product.html ###
@app.route("/single-product.html/<product_id>", methods=["GET", "POST"])
def single_product(product_id):
    product = ProductTable.query.get(product_id)

    if request.method == "GET":
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

    elif request.method == "POST":
        selected_size = request.form.get("size")
        selected_quantity = request.form.get("quantity")

        # Perform actions with the selected size and quantity (e.g., add to cart)
        # You can redirect to the cart page or perform additional logic here

        return redirect(url_for("cart_display"))

    return render_template("single-product.html", product=product, sizes=sizes)


### END ###


### Rout to display the cart content ###
@app.route("/cart")
def cart_display():
    # To retrieve the user in subsequent requests:
    customerID = session.get("user_id")
    return render_template("cart.html")


### END ###


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5002, debug=True)
