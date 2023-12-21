from flask import Flask, render_template
import random
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from faker import Faker


app = Flask(__name__)


# @app.route("/")
# def index():
# return render_template("index.html")

# Create the database if it doesn't exist
engine = create_engine(
    "sqlite:///onlineshop_.db", echo=True, connect_args={"check_same_thread": False}
)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///onlineshop_database.db"  # SQLite URI
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class CustomerTable(db.Model):
    customer_id = db.Column(db.Integer, primary_key=True)
    # firstname = db.Column(db.String(255))
    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone_no = db.Column(db.String(255))
    username = db.Column(db.String(255))
    password = db.Column(db.String(12))


@app.route("/")
def index():
    # Insert random data into the database
    # fake = Faker(['it_IT', 'en_US', 'ja_JP'])
    fake = Faker()
    for _ in range(10):  # Adjust as needed
        new_record = CustomerTable(
            name="John Doe",
            email="john@example.com",
            phone_no="123-456-7890",
            username="johndoe",
            password="password123",
        )
        db.session.add(new_record)

    db.session.commit()

    # Fetch and display data
    records = CustomerTable.query.all()
    return render_template("index.html", records=records)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
