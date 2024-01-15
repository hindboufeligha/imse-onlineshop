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
from lib.database_functions import *
from lib.migration_functions import *
from functools import wraps

app = Flask(__name__, static_folder="assets", template_folder="templates")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SECRET_KEY"] = "a)b@c!(d@e#fg%hi^j&k"
Session(app)
bcrypt = Bcrypt(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///onlineshop_.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["UPLOAD_FOLDER"] = "assets/images"

app.config["DB_MIGRATION_STATUS"] = ""

app.config["MONGO_URI"] = "mongodb://localhost:27017/imse_onlineshop"
mongo = PyMongo(app)

reset_mongodb(mongo)
# access the MongoDB database using the 'db' attribute of the 'mongo' object
mongo_db = mongo.db


# Explicitly set the template folder
# app.template_folder = "templates"

# engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
db.init_app(app)


# Count the number of records in the CategoryTable
def is_category_table_empty():
    # Count the number of records in the CategoryTable
    count = db.session.query(CategoryTable).count()
    # Check if the count is zero
    return count == 0





@app.route("/db_migration")
def db_migration():
    customer_id = session.get("user_id")
    if customer_id:
        customer_data = fetchCustomerData(customer_id, db)

        return render_template("db_migration.html", user_data=customer_data)




@app.route("/")
def DB_operation():
    session["db_status"] = "SQL"
    return render_template("DB_operation.html")


@app.route("/db_migrate")
def db_migrate():
    if session.get("db_status") == "SQL":
        # migrate from sqlite to mongodb:
        migrate_all_data(db, mongo_db)
        # sql_drop_all(db=db)
        # empty_tables(app, db)

        # adjust migration status config:
        app.config["DB_MIGRATION_STATUS"] = "NoSQL"
        session["db_status"] = "NoSQL"
        flash(message=f"Migration to NoSQL completed.", category="success")
        return redirect(url_for("index"))
    else:
        flash(message="You already migrated to NoSQL.", category="info")
        return redirect(url_for("db_migration"))


def is_db_initialized(f):
    """ check if database has been initialized """
    @wraps(f)
    def wrap(*args, **kwargs):
        if app.config['DB_MIGRATION_STATUS'] in ['SQL', 'NoSQL']:
            return f(*args, **kwargs)
        else:
            flash(message='Unauthorized. Please initialize database.', category='danger')
            return redirect(url_for('DB_operation'))
    return wrap





@app.route("/fill_database", methods=["POST"])
def fill_database():
    count = is_category_table_empty()
    initialize_tables(db, count)
    app.config["DB_MIGRATION_STATUS"] = "SQL"
    session["db_status"] = "SQL"
    # Stay at the same page
    return redirect(url_for("DB_operation"))


@app.route("/empty_database", methods=["POST"])
def empty_database():
    empty_tables(app, db)
    # Stay at the same page:
    return redirect(url_for("DB_operation"))



@app.route("/login", methods=["GET"])
@is_db_initialized
def show_login():
    return render_template("login.html")



@app.route("/login", methods=["POST"])
@is_db_initialized
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    user, is_valid = validate_user_credentials(email, password)
    if is_valid:
        session["user_id"] = user.customer_id
        flash(message="Welcome back!", category="success")
        return redirect(url_for("index"))
    else:
        error_message = "Invalid email or password. Please try again."
        return render_template("login.html", error_message=error_message)


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("show_login"))


@app.route("/signup", methods=["GET"])
@is_db_initialized
def show_signup():
    return render_template("signup.html")



@app.route("/signup", methods=["POST"])
@is_db_initialized
def signup():
    firstname = request.form.get("firstname")
    familyname = request.form.get("familyname")
    email = request.form.get("email")
    phone_no = request.form.get("phone_no")
    username = request.form.get("username")
    password = request.form.get("password")

    # Check if the email is already in use
    if checkExistingUser(email):
        flash("Email already in use. Please choose another email.", "danger")
        return redirect(url_for("show_signup"))

    # Create a new customer:
    add_customer(
        firstname=firstname,
        familyname=familyname,
        email=email,
        phone_no=phone_no,
        username=username,
        password=password,
    )

    flash("Account created successfully! You can now log-in.", "success")
    return redirect(url_for("show_login"))



@app.route("/index")
@is_db_initialized
def index():
    user_id = session.get("user_id")
    if user_id:
        user_data = userData(user_id)
        if user_data:
            top_male_products = TopProducts("Male")
            top_female_products = TopProducts("Female")
            top_kids_products = TopProducts("Children")

            return render_template(
                "index.html",
                user_data=user_data,
                top_male_products=top_male_products,
                top_female_products=top_female_products,
                top_kids_products=top_kids_products,
                category="success",
            )
        else:
            return "User data not found", 404
    else:
        return redirect(url_for("show_login"))



# organized review codes
@app.route("/my_reviews")
@is_db_initialized
def reviews():
    user_id = session.get("user_id")
    if user_id:
        user_reviews, user_data = userReviews(user_id)
        if not user_data:
            return "User data not found", 404

        return render_template(
            "reviews.html", reviews=user_reviews, user_data=user_data
        )
    else:
        return redirect(url_for("show_login"))


@app.route("/delete_review/<int:review_id>", methods=["POST"])
@is_db_initialized
def delete_review(review_id):
    result, message = deleteUserReview(review_id)
    return jsonify({"message": message}), result


@app.route("/add-review/<int:product_id>", methods=["GET", "POST"])
@is_db_initialized
def add_review(product_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("show_login"))

    user_data = userData(user_id)
    if not user_data:
        flash("User data not found", "error")
        return redirect(url_for("index"))

    product = getProduct(product_id)
    if not product:
        flash("Product not found", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        rating = float(request.form.get("rating"))

        getCreateReview(user_id, product_id, title, description, rating)
        flash("Review saved successfully", "success")
        return redirect(url_for("reviews"))

    existing_review = getCreateReview(user_id, product_id, get_only=True)
    return render_template(
        "add-review.html", user_data=user_data, product=product, review=existing_review
    )


@app.route("/submit_review", methods=["POST"])
@is_db_initialized
def submit_review():
    title = request.form.get("title")
    description = request.form.get("description")
    rating = request.form.get("rating")
    product_id = request.form.get(
        "product_id"
    )  

    if not product_id:
        return "Product ID is required", 400

    # Process image upload if available
    image = request.files.get("image")
    image_url = None
    if image and image.filename != "":
        filename = secure_filename(image.filename)
        image_save_directory = os.path.join(app.static_folder, "uploads/reviews")
        os.makedirs(image_save_directory, exist_ok=True)

        image_path = os.path.join(image_save_directory, filename)
        image.save(image_path)

        image_url = url_for("static", filename=f"uploads/reviews/{filename}")

    user_id = session.get("user_id")
    submitUpdateReview(user_id, product_id, title, description, rating, image_url)

    flash("success", "Review submitted successfully") 
    return redirect(url_for("reviews"))


@app.route("/search_reviews", methods=["POST"])
@is_db_initialized
def search_reviews():
    search_query = request.form.get("searchQueryInput", "")
    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("show_login"))

    user_data = userData(user_id)
    if not user_data:
        return "User data not found", 404

    if request.method == "POST":
        search_query = request.form.get("searchQueryInput", "")
        matched_reviews = searchReviews(search_query)
        return render_template(
            "reviews.html", user_data=user_data, reviews=matched_reviews
        )
    else:
        return render_template("order_list.html", user_data=user_data)


@app.route("/order_list")
@is_db_initialized
def order_list():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("show_login"))

    user_data = userData(user_id)
    if not user_data:
        return "User data not found", 404

    associated_products = associatedProducts(user_id)
    return render_template(
        "order_list.html", user_data=user_data, products=associated_products
    )


@app.route("/search_products", methods=["GET", "POST"])
@is_db_initialized
def search_products():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("show_login"))

    user_data = userData(user_id)
    if not user_data:
        return "User data not found", 404

    if request.method == "POST":
        search_query = request.form.get("searchQueryInput", "")
        matched_products = searchProducts(search_query)
        return render_template(
            "order_list.html", user_data=user_data, products=matched_products
        )
    else:
        return render_template("order_list.html", user_data=user_data)



## Cookies --->

## End of Cookies --->



@app.route("/psubcategory")
@is_db_initialized
def psubcategory():
    p_gender = request.args.get("p_gender")
    return render_template("p-subcategory.html", p_gender=p_gender)


@app.route("/products")
@is_db_initialized
def products():
    category_name = request.args.get("category_name")
    parent_category_id = request.args.get("parent_category_id")
    p_gender = request.args.get("p_gender")
    customer_id = session.get("user_id")

    if customer_id:
        user_data = fetchCustomerData(customer_id, db)
        if user_data:
            # Fetch products based on category_name, parent_category_id, and gender
            products_with_categories = displayProducts(request, db)
            return render_template(
                "products.html",
                products_with_categories=products_with_categories,
                user_data=user_data,
                category_name=category_name,
                p_gender=p_gender,
            )


### Display Products based on the gender in products.html ###
# from index, when the user clicks on discover --> depends on the gender --> will be redirected to this page products.html
@app.route("/products/<gender>")
@is_db_initialized
def display_products(gender):
    products = displayGenderProducts(gender, db)
    customer_id = session.get("user_id")

    if customer_id:
        user_data = fetchCustomerData(customer_id, db)
        if user_data:
            # Render the products page with the user's data
            return render_template(
                "products.html", user_data=user_data, products=products, p_gender=gender
            )


### END ###


### Route to display the selected Product details on single-product.html ###
@app.route("/single-product.html/<product_id>", methods=["GET", "POST"])
@is_db_initialized
def single_product(product_id):
    product = fetchProductData(product_id, db)
    if request.method == "GET":
        sizes = displaySingleProduct(product_id, request, db)

    elif request.method == "POST":
        # selected_size = request.form.get("size")
        # selected_quantity = request.form.get("quantity")
        # Perform actions with the selected size and quantity (e.g., add to cart)
        # You can redirect to the cart page or perform additional logic here
        # A MODIER PLUS TARD
        add_to_cart()
        return redirect(url_for("cart_display"))

    customer_id = session.get("user_id")
    if customer_id:
        user_data = fetchCustomerData(customer_id, db)
        if user_data:
            return render_template(
                "single-product.html", user_data=user_data, product=product, sizes=sizes
            )


### END ###


### Route to display the Cart's Content ###
@app.route("/cart")
@is_db_initialized
def cart_display():
    customer_id = session.get("user_id")

    if customer_id:
        user_data = fetchCustomerData(customer_id, db)
        if user_data:
            cart_items = displayCartItems(customer_id, db)

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

            # Render the products page with the user's data and cart_items:
            return render_template(
                "cart.html",
                user_data=user_data,
                cart_items=cart_items,
                items=cart_items_quantity_price,
            )


### END ###


### Route to add items to the Cart: Backend ###
@app.route("/add_to_cart", methods=["POST"])
@is_db_initialized
def add_to_cart():
    customer_id = session.get("user_id")
    try:
        addToCart(customer_id, request, db)
        return jsonify({"message": "Item added to the cart successfully!"}), 200

    except IntegrityError:
        # Handle integrity error (e.g., duplicate entry)
        db.session.rollback()
        return jsonify({"error": "Integrity error occurred"}), 400

    except FlushError:
        # Handle flush error
        db.session.rollback()
        return jsonify({"error": "Flush error occurred"}), 400

    except Exception as e:
        # Handle other exceptions
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


### END ###


### Hind Boufeligha REPORTING: Product Popularity ##
### Route to the most Popular Products in each Category within the last 6 month ###
@app.route("/popular_products")
@is_db_initialized
def popular_products():
    customer_id = session.get("user_id")

    if customer_id:
        customer_data = fetchCustomerData(customer_id, db)
        popular_products = displayPopularProducts(db)

        return render_template(
            "popular_products.html",
            user_data=customer_data,
            products=popular_products,
        )


### END ###


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5002, debug=True)
