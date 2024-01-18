import pymongo
import pandas as pd
from lib.init_database_functions import *
from sqlalchemy import select, join
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy import text


def reset_mongodb(mongo):
    # delete all data from previous runs:
    mongo.cx.drop_database(mongo.db.name)


def migrate_all_data(db, mongo_db):
    # Data Frames

    # 1: fetch data from SQLite db:
    stmt = select("*").select_from(CustomerTable)
    # sql_query = text("SELECT * FROM customer_table")
    df_customer = pd.read_sql(stmt, con=db.engine)

    stmt = select("*").select_from(AddressTable)
    df_address = pd.read_sql(stmt, con=db.engine)

    stmt = select("*").select_from(ProductTable)
    df_product = pd.read_sql(stmt, con=db.engine)

    stmt = select("*").select_from(CategoryTable)
    df_category = pd.read_sql(stmt, con=db.engine)

    stmt = select("*").select_from(ReviewTable)
    df_review = pd.read_sql(stmt, con=db.engine)

    stmt = select("*").select_from(CartTable)
    df_cart = pd.read_sql(stmt, con=db.engine)

    stmt = select("*").select_from(CartItemTable)
    df_cartitem = pd.read_sql(stmt, con=db.engine)

    stmt = select("*").select_from(PaymentTable)
    df_payment = pd.read_sql(stmt, con=db.engine)

    stmt = select("*").select_from(WishlistTable)
    df_wishlist = pd.read_sql(stmt, con=db.engine)

    stmt = select("*").select_from(SizeTable)
    df_size = pd.read_sql(stmt, con=db.engine)

    # Perform SQL query to get products associated with wishlists from the join table wishlist_product_association

    sql_query = text("SELECT * FROM customer_product_association")
    df_order = pd.read_sql(sql_query, con=db.engine)

    sql_query = text("SELECT * FROM wishlist_product_association")
    df_wishlist_product = pd.read_sql(sql_query, con=db.engine)

    sql_query = text("SELECT * FROM product_size_association")
    df_product_size = pd.read_sql(sql_query, con=db.engine)

    # 2: rename index column and fix datetime format
    df_customer.rename(columns={"customer_id": "_id"}, inplace=True)
    df_product.rename(columns={"p_id": "_id"}, inplace=True)
    df_category.rename(columns={"category_id": "_id"}, inplace=True)
    df_review.rename(columns={"ReviewID": "_id"}, inplace=True)
    df_cart.rename(columns={"cart_id": "_id"}, inplace=True)
    df_cartitem.rename(columns={"cart_item_id": "_id"}, inplace=True)
    df_payment.rename(columns={"payment_id": "_id"}, inplace=True)
    df_wishlist.rename(columns={"wishlist_id": "_id"}, inplace=True)
    df_size.rename(columns={"size_id": "_id"}, inplace=True)

    df_cart["creation_date"] = pd.to_datetime(df_cart["creation_date"])
    df_review["post_date"] = pd.to_datetime(df_review["post_date"])
    df_payment["payment_date"] = pd.to_datetime(df_payment["payment_date"])
    df_order["order_date"] = pd.to_datetime(df_order["order_date"])

    # 3: create Customer Collection in mongodb and embed Address
    customer_col = mongo_db["customer"]
    customer_col.create_index([("_id", pymongo.ASCENDING)])

    # merge Customer and Address dataframes to embed address:
    # df_merged = pd.merge(df_customer, df_address, left_on="_id", right_on="customer_id", how="left")
    # drop the address id column from the merged dataframe:
    # df_merged.drop("address_id", axis=1, inplace=True)

    customers = df_customer.to_dict(orient="records")

    # Embed Addresses within each Customer document:
    for customer in customers:
        customer_id = customer["_id"]
        # Extract cartitems related to the current cart_id
        addresses = df_address[df_address["customer_id"] == customer_id].to_dict(
            orient="records"
        )

        # Remove customer_id from each address dictionary
        for address in addresses:
            address.pop("customer_id", None)

        # Embed Addresses within each Customer document:
        customer["addresses"] = addresses

    # Embed wishlists within each customer document:
    for customer in customers:
        customer_id = customer["_id"]
        wishlists = df_wishlist[df_wishlist["customer_id"] == customer_id].to_dict(
            orient="records"
        )

        # Reference to Product IDs within each Wishlist Document:
        for wishlist in wishlists:
            wishlist_id = wishlist["_id"]
            wishlist_product_ids = df_wishlist_product[
                df_wishlist_product["wishlistID"] == wishlist_id
            ]["productID"].tolist()

            wishlist["product_ids"] = wishlist_product_ids

        # Remove customer_id from each wishlists dictionary
        for wishlist in wishlists:
            wishlist.pop("customer_id", None)

        customer["wishlists"] = wishlists

    # REFERENCING TO ORDERS IDs(customer)

    customer_col.insert_many(customers)

    # 4: create Product Collection in mongodb and embed Category
    # Merge Product and Category dataframes to embed category info within product:
    df_merged = pd.merge(df_product, df_category, on="_id", how="left")

    # create Product Collection in mongodb
    product_col = mongo_db["product"]  # OR: product_collection = mongo_db.db.product

    # Indexing:
    product_col.create_index([("_id", pymongo.ASCENDING)])
    product_col.create_index([("category._id", pymongo.ASCENDING)])

    # products = [row.dropna().to_dict() for _, row in df_product.iterrows()]
    # col.insert_many(products)

    # Convert the merged dataframe to a list of dictionaries and insert into MongoDB
    products = df_merged.to_dict(orient="records")

    # Embed Sizes within each Product document:
    for product in products:
        product_id = product["_id"]
        # Extract cartitems related to the current cart_id
        sizes = df_product_size[df_product_size["p_id"] == product_id].to_dict(
            orient="records"
        )
        # Remove p_id from each size dictionary
        for size in sizes:
            size.pop("p_id", None)

            # fetch size_name info from df_size
            size_id = size.get("size_id")
            if size_id is not None:
                size_info = df_size[df_size["_id"] == size_id].to_dict(orient="records")
                if size_info:
                    size_name = size_info[0]["size_name"]
                    size["size_name"] = size_name

        # Embed Sizes within each Product document:
        product["sizes"] = sizes

    product_col.insert_many(products)

    # 5: create Cart Collection in mongodb and embed Payment and reference to customer_id:
    # Merge Cart and Payment dataframes to embed payment info within cart:
    df_merged = pd.merge(df_cart, df_payment, on="_id", how="left")

    # create Cart Collection in mongodb
    cart_col = mongo_db["cart"]  # OR: product_collection = mongo_db.db.product

    # Indexing:
    cart_col.create_index(
        [
            ("_id", pymongo.ASCENDING),
            ("customer_id", pymongo.ASCENDING),
            ("status", pymongo.ASCENDING),
        ],
        unique=True,
    )

    # Replace NaT values with None before converting to a dictionary
    # df_merged_cleaned = df_merged.applymap(lambda x: None if pd.isna(x) else x)

    # Convert the Cart DataFrame to a list of dictionaries
    carts = df_cart.to_dict(orient="records")

    # Embed Payment within each Cart document:
    for cart in carts:
        cart_id = cart["_id"]
        # Extract cartitems related to the current cart_id
        payment = df_payment[df_payment["cart_id"] == cart_id].to_dict(orient="records")

        # Embed Payment record within each Cart document:
        cart["payment_info"] = payment

    # Embed CartItems within each Cart document:
    for cart in carts:
        cart_id = cart["_id"]
        # Extract cartitems related to the current cart_id
        cartitems = df_cartitem[df_cartitem["cart_id"] == cart_id].to_dict(
            orient="records"
        )

        # Remove cart_id from each size dictionary
        for cartitem in cartitems:
            cartitem.pop("cart_id", None)

        # Embed CartItem within each Cart document:
        cart["cart_items"] = cartitems
        # Remove cart_item_id from each cartitems dictionary
        for cart_item in cartitems:
            cart_item.pop("_id", None)

        customer["wishlists"] = wishlists

    # print(carts[:5]) TEST
    # Insert Carts into mongodb:
    cart_col.insert_many(carts)

    # 6: create CartItem Collection in mongodb
    cartitem_col = mongo_db["cartitem"]
    # Indexing:
    cartitem_col.create_index(
        [
            ("_id", pymongo.ASCENDING),
            ("cart_id", pymongo.ASCENDING),
            ("product_id", pymongo.ASCENDING),
        ],
        unique=True,
    )
    cartitems = [row.dropna().to_dict() for _, row in df_cartitem.iterrows()]
    cartitem_col.insert_many(cartitems)

    # 7: create Order Collection in mongodb:
    # Rename columns to align with MongoDB document structure
    df_order.rename(
        columns={"customerID": "customer_id", "productID": "product_id"}, inplace=True
    )
    df_order["order_date"] = pd.to_datetime(df_order["order_date"])

    orders = df_order.to_dict(orient="records")

    # Create Order Collection in MongoDB and index it
    order_col = mongo_db["order"]
    order_col.create_index([("customer_id", pymongo.ASCENDING)])
    order_col.create_index([("product_id", pymongo.ASCENDING)])
    order_col.create_index([("order_date", pymongo.ASCENDING)])

    # Insert Orders into MongoDB
    order_col.insert_many(orders)

    # 8: create review Collection in mongodb and refrence it with customer_id and product_id
    # Transform Review DataFrame for MongoDB
    df_review.rename(
        columns={"customer_id": "customer_id", "product_id": "product_id"}, inplace=True
    )
    df_review["post_date"] = pd.to_datetime(df_review["post_date"])

    # Convert Review DataFrame to a list of dictionaries
    reviews = df_review.to_dict(orient="records")

    # Create Review Collection in MongoDB and index it
    review_col = mongo_db["review"]
    review_col.create_index([("_id", pymongo.ASCENDING)])
    review_col.create_index([("customer_id", pymongo.ASCENDING)])
    review_col.create_index([("product_id", pymongo.ASCENDING)])

    # Insert Reviews into MongoDB
    review_col.insert_many(reviews)

    # 9: create Size collection in mongodb:
    size_col = mongo_db["size"]
    size_col.create_index([("_id", pymongo.ASCENDING)])
    sizes = df_size.to_dict(orient="records")

    size_col.insert_many(sizes)
