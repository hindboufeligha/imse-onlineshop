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

import os
import random
import sqlite3
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from lib.init_database_functions import *


app = Flask(__name__, static_folder="assets", template_folder="templates")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = "a)b@c!(d@e#fg%hi^j&k"
Session(app)
bcrypt = Bcrypt(app)

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
    user_id = session.get('user_id')
    if user_id:
        user_data = CustomerTable.query.filter_by(customer_id=user_id).first()
        if not user_data:
            return "User data not found", 404

        product_id = request.args.get('product_id')
        if product_id:
            product = ProductTable.query.get(product_id)
            if product:
                return render_template("add-review.html", user_data=user_data, product=product)
            else:
                return "Product not found", 404
        else:
            return "Product ID is required", 400
    else:
        # Redirect to login if no user is in session
        return redirect(url_for("show_login"))

    
    
@app.route("/submit_review", methods=["POST"])
def submit_review():
    product_id = request.form.get('product_id')
    if product_id:
        title = request.form['title']
        description = request.form['description']
        rating = request.form['rating']
        
        # Process image upload if available
        image = request.files.get('image')
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            image_save_directory = os.path.join(app.static_folder, 'uploads/reviews')
            os.makedirs(image_save_directory, exist_ok=True)

            image_path = os.path.join(image_save_directory, filename)
            image.save(image_path)

            image_url = url_for('static', filename=f'uploads/reviews/{filename}')
        else:
            image_url = None  # or a default image URL

        new_review = ReviewTable(
            title=title,
            description=description,
            rating=rating,
            image_url=image_url,
            customer_id=session.get('user_id'),
            product_id=product_id
        )
        db.session.add(new_review)
        db.session.commit()
        return "Review submitted successfully"  # Or redirect to another page
    else:
        return "Product ID is required", 400



@app.route("/order_list")
def order_list():
    user_id = session.get('user_id')
    if user_id:
        user_data = CustomerTable.query.filter_by(customer_id=user_id).first()
        if user_data:
            # Query to find product IDs associated with the user
            associated_product_ids = db.session.query(customer_product_association.c.productID).filter(
                customer_product_association.c.customerID == user_id
            ).all()

            # Fetch the products using the retrieved product IDs
            product_ids = [pid[0] for pid in associated_product_ids]
            associated_products = ProductTable.query.filter(ProductTable.p_id.in_(product_ids)).all()

            # Pass both user_data and products to the template
            return render_template("order_list.html", user_data=user_data, products=associated_products)
        else:
            return "User data not found", 404
    else:
        return redirect(url_for("show_login"))



@app.route("/search_products", methods=["GET", "POST"])
def search_products():
    user_id = session.get('user_id')
    if user_id:
        user_data = CustomerTable.query.filter_by(customer_id=user_id).first()
        if not user_data:
            return "User data not found", 404

        if request.method == "POST":
            search_query = request.form.get("searchQueryInput", "")
            matched_products = ProductTable.query.filter(ProductTable.p_name.like(f"%{search_query}%")).all()
            return render_template("order_list.html", user_data=user_data, products=matched_products)
        else:
            return render_template("order_list.html", user_data=user_data)

    else:
        return redirect(url_for("show_login"))




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
    user = CustomerTable.query.filter_by(email=email).first()

    if user and bcrypt.check_password_hash(user.password, password):
        session["user_id"] = user.customer_id
        return redirect(url_for("index"))

    else:
        # Invalid credentials, render the login page with an error message
        error_message = "Invalid email or password. Please try again."
        return render_template("login.html", error_message=error_message)


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("show_login"))


@app.route("/signup", methods=["GET"])
def show_signup():
    return render_template("signup.html")


@app.route("/signup", methods=["POST"])
def signup():
    firstname = request.form.get("firstname")
    familyname = request.form.get("familyname")
    email = request.form.get("email")
    phone_no = request.form.get("phone_no")
    username = request.form.get("username")
    password = request.form.get("password")

    # Check if the email is already in use
    existing_user = CustomerTable.query.filter_by(email=email).first()
    if existing_user:
        flash("Email already in use. Please choose another email.", "danger")
        return redirect(url_for("show_signup"))

    # Hash the password securely
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    # Create a new user
    new_user = CustomerTable(
        firstname=firstname,
        familyname=familyname,
        email=email,
        phone_no=phone_no,
        username=username,
        password=hashed_password,
    )

    db.session.add(new_user)
    db.session.commit()

    flash("Account created successfully. You can now log in.", "success")
    return redirect(url_for("show_login"))


## Cookies --->

## End of Cookies --->


@app.route("/")
def DB_operation():
    return render_template("DB_operation.html")


@app.route("/index")
def index():
    user_id = session.get("user_id")
    if user_id:
        user_data = CustomerTable.query.filter_by(customer_id=user_id).first()
        if user_data:
            # Pass user_data to the template
            return render_template("index.html", user_data=user_data)
        else:
            # Handle case where user data is not found
            return "User data not found", 404
    else:
        # Redirect to login if no user is in session
        return redirect(url_for("show_login"))


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
    user_id = session.get("user_id")
    if user_id:
        user_data = CustomerTable.query.filter_by(customer_id=user_id).first()
        if user_data:
            # Render the products page with the user's data
            return render_template(
                "products.html", user_data=user_data, products=products, p_gender=gender
            )


### END ###

### Route to display the selected Product details on single-product.html ###
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
        # A MODIER PLUS TARD
        return redirect(url_for("cart_display"))

    user_id = session.get("user_id")
    if user_id:
        user_data = CustomerTable.query.filter_by(customer_id=user_id).first()
        if user_data:
            return render_template(
                "single-product.html", user_data=user_data, product=product, sizes=sizes
            )


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
