from flask import Flask, render_template
import random
import sqlite3
from flask_sqlalchemy import (
    SQLAlchemy,
)  # to define the tables, relationships, and associations in our Online Shop Web Application.
from sqlalchemy import create_engine
from faker import Faker
from datetime import datetime

app = Flask(__name__)


# @app.route("/")
# def index():
# return render_template("index.html")

# Create the database if it doesn't exist
engine = create_engine(
    "sqlite:///onlineshop_.db", echo=True, connect_args={"check_same_thread": False}
)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///onlineshop_.db"  # SQLite URI
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# Join table for N:M relationship between Customers and Products
customer_product_association = db.Table(
    "customer_product_association",
    db.Column("customerID", db.Integer, db.ForeignKey("customer_table.customer_id")),
    db.Column("productID", db.Integer, db.ForeignKey("product_table.p_id")),
)

# association table for Wishlist and Product
wishlist_product_association = db.Table(
    "wishlist_product_association",
    db.Column("wishlistID", db.Integer, db.ForeignKey("wishlist_table.wishlist_id")),
    db.Column("productID", db.Integer, db.ForeignKey("product_table.p_id")),
)


class CustomerTable(db.Model):
    __tablename__ = "customer_table"
    customer_id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(255))
    familyname = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone_no = db.Column(db.String(255))
    username = db.Column(db.String(255))
    password = db.Column(db.String(12))

    products = db.relationship(
        "ProductTable",
        secondary=customer_product_association,
        backref="associated_customers",
        lazy=True,
    )

    addresses = db.relationship("AddressTable", backref="customer", lazy=True)
    reviews = db.relationship("ReviewTable", backref="customer", lazy=True)
    wishlists = db.relationship("WishlistTable", backref="customer", lazy=True)
    carts = db.relationship("CartTable", backref="customer", lazy=True)


class AddressTable(db.Model):
    __tablename__ = "address_table"
    address_id = db.Column(db.Integer, primary_key=True)
    address_title = db.Column(db.String(255))  # home / office / other
    street_name = db.Column(db.String(255))
    house_no = db.Column(db.String(255))
    floor_no = db.Column(db.String(255))
    appartment_no = db.Column(db.String(255))
    city = db.Column(db.String(12))
    postalcode = db.Column(db.String(12))
    country = db.Column(db.String(12))

    customer_id = db.Column(
        db.Integer, db.ForeignKey("customer_table.customer_id"), nullable=False
    )


class ProductTable(db.Model):
    __tablename__ = "product_table"
    p_id = db.Column(db.Integer, primary_key=True)
    p_name = db.Column(db.String(255))
    p_description = db.Column(db.String(255))
    p_price = db.Column(db.String(255))
    p_gender = db.Column(db.String(255))
    p_size_variation = db.Column(db.String(255))

    reviews = db.relationship("ReviewTable", backref="product", lazy=True)
    customers = db.relationship(
        "CustomerTable",
        secondary=customer_product_association,
        backref="associated_products",
        lazy=True,
    )

    category_id = db.Column(
        db.Integer, db.ForeignKey("category_table.category_id"), nullable=False
    )

    cart_items = db.relationship("CartItemTable", backref="product", lazy=True)


class CategoryTable(db.Model):
    __tablename__ = "category_table"
    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    parent_category_id = db.Column(
        db.Integer, db.ForeignKey("category_table.category_id")
    )

    subcategories = db.relationship(
        "CategoryTable",
        backref=db.backref("parent_category", remote_side=[category_id]),
    )
    products = db.relationship("ProductTable", backref="category", lazy=True)


class CartTable(db.Model):
    __tablename__ = "cart_table"
    cart_id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    customer_id = db.Column(
        db.Integer, db.ForeignKey("customer_table.customer_id"), nullable=False
    )

    cart_items = db.relationship("CartItemTable", backref="cart", lazy=True)
    payment = db.relationship("PaymentTable", backref="cart", uselist=False)


class CartItemTable(db.Model):
    __tablename__ = "cartitem_table"
    cart_item_id = db.Column(db.Integer, primary_key=True)
    size = db.Column(db.String(10))
    quantity = db.Column(db.Integer, nullable=False)

    cart_id = db.Column(db.Integer, db.ForeignKey("cart_table.cart_id"), nullable=False)
    product_id = db.Column(
        db.Integer, db.ForeignKey("product_table.p_id"), nullable=False
    )


class PaymentTable(db.Model):  # 1:1 with Cart
    __tablename__ = "payment_table"
    payment_id = db.Column(db.Integer, primary_key=True)
    payment_method = db.Column(db.String(50), nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    cart_id = db.Column(
        db.Integer, db.ForeignKey("cart_table.cart_id"), unique=True, nullable=False
    )


class ReviewTable(db.Model):
    __tablename__ = "review_table"
    ReviewID = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text)
    rating = db.Column(db.Float, nullable=False)
    post_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    customer_id = db.Column(
        db.Integer, db.ForeignKey("customer_table.customer_id"), nullable=False
    )

    product_id = db.Column(
        db.Integer, db.ForeignKey("product_table.p_id"), nullable=False
    )


class WishlistTable(db.Model):
    __tablename__ = "wishlist_table"
    wishlist_id = db.Column(db.Integer, primary_key=True)
    wishlist_name = db.Column(db.String(50), nullable=False)

    customer_id = db.Column(
        db.Integer, db.ForeignKey("customer_table.customer_id"), nullable=False
    )

    products = db.relationship(
        "ProductTable",
        secondary=wishlist_product_association,
        backref="wishlists",
        lazy=True,
    )


@app.route("/")
def index():
    # Insert random data into the database
    # fake = Faker()
    fake = Faker(["de_AT"])  # generate data in Austrian Deutsch
    for _ in range(10):  # 10 records
        new_customer = CustomerTable(
            firstname=fake.first_name(),
            familyname=fake.last_name(),
            email=fake.email(),
            phone_no=fake.phone_number(),
            username=fake.user_name(),
            password=fake.password(
                length=8,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ),
        )

        # gnerate 1-2 random address for each customer:
        for _ in range(fake.random_int(min=1, max=2)):
            new_address = AddressTable(
                address_title=fake.random_element(elements=("Home", "Office", "Other")),
                street_name=fake.street_address(),
                house_no=fake.building_number(),
                floor_no=fake.random_int(min=1, max=10),
                appartment_no=fake.random_int(min=1, max=10),
                city=fake.city(),
                postalcode=fake.postcode(),
                country="Austria",
            )

            # add this new address to the addresses list of this customer:
            new_customer.addresses.append(new_address)

        # add this new customer to the DB
        db.session.add(new_customer)

    # commit changes to the DB:
    db.session.commit()

    # Fetch and display data:
    customers = CustomerTable.query.all()
    return render_template("index.html", customers=customers)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
