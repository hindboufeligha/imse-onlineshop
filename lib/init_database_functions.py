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

db = SQLAlchemy()

# def create_database(app):
# with app.app_context():
# db.create_all()

# Join table for N:M relationship between Customers and Products:
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

product_size_association = db.Table(
    "product_size_association",
    db.Column("p_id", db.Integer, db.ForeignKey("product_table.p_id")),
    db.Column("size_id", db.Integer, db.ForeignKey("size_table.size_id")),
    db.Column("quantity", db.Integer, nullable=False),
    # db.Column('price_per_unit', db.DECIMAL(10, 2)),
    # db.Column('discount_percentage', db.DECIMAL(5, 2)),
    db.PrimaryKeyConstraint("p_id", "size_id"),
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
    # p_size_variation = db.Column(db.String(255))
    p_image_url = db.Column(db.String(255))
    # p_quantity = db.Column(db.Integer)
    reviews = db.relationship("ReviewTable", backref="product", lazy=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("category_table.category_id"), nullable=False
    )

    cart_items = db.relationship("CartItemTable", backref="product", lazy=True)
    sizes = db.relationship(
        "SizeTable",
        secondary=product_size_association,
        backref="products_with_quantities",
    )


class SizeTable(db.Model):
    __tablename__ = "size_table"
    size_id = db.Column(db.Integer, primary_key=True)
    size_name = db.Column(db.String(255), nullable=False)


# CREATE TABLE Product_Size (
# product_id INT,
# size_id INT,
# quantity INT,
# price_per_unit DECIMAL(10, 2),
# discount_percentage DECIMAL(5, 2),
# PRIMARY KEY (product_id, size_id),
# FOREIGN KEY (product_id) REFERENCES Product(product_id),
# FOREIGN KEY (size_id) REFERENCES Size(size_id)
# );


class CategoryTable(db.Model):
    __tablename__ = "category_table"
    category_id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(50), nullable=False)
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
        db.Integer,
        db.ForeignKey("cart_table.cart_id"),
        unique=True,
        nullable=False,
    )


class ReviewTable(db.Model):
    __tablename__ = "review_table"
    ReviewID = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
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


def initialize_tables(db, count):
    # with app.app_context():
    # 1: Insert random data of Customers into the DB:
    fake = Faker(["de_AT"])  # generate data in Austrian Deutsch
    for _ in range(10):  # 10 customers
        new_customer = CustomerTable(
            firstname=fake.first_name(),
            familyname=fake.last_name(),
            email=fake.email(),
            # phone_no=fake.phone_number(),
            phone_no=fake.numerify(text="+43 ###########"),
            username=fake.user_name(),
            password=fake.password(
                length=8,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ),
        )

        # generate 1-2 random address for each customer:
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

        # generate 1-2 random wishlists for each customer:
        for _ in range(fake.random_int(min=1, max=2)):
            new_wishlist = WishlistTable(
                wishlist_name=fake.word(),
            )

        # add this new address to the addresses list of this customer:
        new_customer.wishlists.append(new_wishlist)
        # add this new customer to the DB
        db.session.add(new_customer)

    # 2: Insert Categories:
    # Insert Categories for once
    if count != 0:
        # List of Categories and Sub-categories:
        categories = [
            ("Shirts", "Clothing"),
            ("Jeans", "Clothing"),
            ("Pyjamas", "Clothing"),
            ("Jackets & Coats", "Clothing"),
            ("Hoodies", "Clothing"),
            ("Sneakers", "Shoes"),
            ("Boots", "Shoes"),
            ("Jewellery", "Accessories"),
            ("Bags", "Accessories"),
            # instead add Children as a gender option
            # ("Clothing for Children", "Clothing"),
            # ("Shoes for Children", "Children"),
            # ("Accessories for Children", "Children"),
        ]
        # define a dic to keep track of parent categories using their names, to store already created parent categories in order to avoid unnecessary DB queries.
        category_objects = {}
        for category_name, parent_category_name in categories:
            # First, Check if the parent category exists:
            parent_category = category_objects.get(parent_category_name)
            if not parent_category:  # parent_category does not exist yet
                parent_category = CategoryTable(category_name=parent_category_name)
                db.session.add(parent_category)
                db.session.commit()
                category_objects[parent_category_name] = parent_category

            # Then, Create sub-category
            subcategory = CategoryTable(
                category_name=category_name,
                parent_category_id=parent_category.category_id,
            )
            db.session.add(subcategory)
            db.session.commit()

    fake = Faker(["de_AT"])
    # 3: Generate 10 Products:
    for _ in range(10):  # 10 products
        # categories_sizes = {
        # "Shoes": ["37", "38", "39", "40"],
        # "Clothing": ["S", "M", "L", "XL"],
        # "Accessories": ["One Size"],
        # }
        gender = random.choice(["Male", "Female", "Children"])
        # size_variation = random.choice([True, False])
        image_url = "https://www.powerreviews.com/wp-content/uploads/2022/07/wardrobe-22-2048x1376.png"
        # make sure to assign products a subcategory:
        subcategory = (
            CategoryTable.query.filter(CategoryTable.parent_category_id.isnot(None))
            .order_by(func.random())
            .first()
        )
        if subcategory:
            new_product = ProductTable(
                p_name=fake.word(),
                p_description=fake.sentence(),
                p_price=round(random.uniform(10, 1000), 2),
                p_gender=gender,
                # p_size_variation=size_variation,
                category_id=subcategory.category_id,
                p_image_url=image_url,
            )
            db.session.add(new_product)
            db.session.commit()

            if (
                subcategory.category_name == "Boots"
                or subcategory.category_name == "Sneakers"
            ):
                sizes = ["37", "38", "39", "40"]

            elif (
                subcategory.category_name == "Jewellery"
                or subcategory.category_name == "Bags"
            ):
                sizes = ["One Size"]

            else:
                sizes = ["S", "M", "L", "XL"]

            # Associate the new product with all its relevant sizes:
            for size_name in sizes:
                size = SizeTable.query.filter_by(size_name=size_name).first()

                if not size:
                    size = SizeTable(size_name=size_name)
                    db.session.add(size)
                    db.session.commit()

                quantity = random.randint(5, 50)
                # price_per_unit = round(random.uniform(5.0, 20.0), 2)
                # discount_percentage = round(random.uniform(0.0, 30.0), 2)
                product_size = product_size_association.insert().values(
                    p_id=new_product.p_id,
                    size_id=size.size_id,
                    quantity=quantity,
                    # price_per_unit=price_per_unit,
                    # discount_percentage=discount_percentage,
                )

                db.session.execute(product_size)
                db.session.commit()

        else:  # if there are no sub-categories:
            print(
                "No sub-category available! Skip the product creation in this iteration."
            )

    # FUNC: randomly add products to wishlists
    # fetch all products and wishlists from DB:
    products = ProductTable.query.all()
    wishlists = WishlistTable.query.all()

    # 5: Randomly add products to wishlists
    # loop through a subset of wishlists and randomly add products to them
    for wishlist in random.sample(wishlists, min(len(wishlists), 2)):
        # number of products to be added to the wishlist:
        num = random.randint(1, min(len(products), 2))
        # add products to each wishlist
        wishlist.products.extend(random.sample(products, num))

    db.session.commit()

    # 6: Randomly associate customers with products (means that the customer has already bought this/those product(s))
    # fetch all customers and products from DB
    customers = CustomerTable.query.all()
    products = ProductTable.query.all()

    # loop through a subset of customers and randomly associate them with some products
    for customer in random.sample(customers, min(len(customers), 2)):
        # number of products to be added to the wishlist:
        num = random.randint(1, min(len(products), 2))
        # add products to each wishlist
        customer.products.extend(random.sample(products, num))

    db.session.commit()
