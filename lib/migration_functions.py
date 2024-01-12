import pymongo
import pandas as pd
from lib.init_database_functions import *
from sqlalchemy import select


def migrate_all_data(db, mongo_db):
    # Data Frames
    # 1: fetch data from SQLite db:
    stmt = select("*").select_from(CustomerTable)
    df_customer = pd.read_sql(stmt, con=db)

    stmt = select("*").select_from(AddressTable)
    df_address = pd.read_sql(stmt, con=db)

    stmt = select("*").select_from(ProductTable)
    df_product = pd.read_sql(stmt, con=db)

    stmt = select("*").select_from(CategoryTable)
    df_category = pd.read_sql(stmt, con=db)

    stmt = select("*").select_from(ReviewTable)
    df_review = pd.read_sql(stmt, con=db)

    stmt = select("*").select_from(CartTable)
    df_cart = pd.read_sql(stmt, con=db)

    stmt = select("*").select_from(CartItemTable)
    df_cartitem = pd.read_sql(stmt, con=db)

    stmt = select("*").select_from(PaymentTable)
    df_payment = pd.read_sql(stmt, con=db)

    stmt = select("*").select_from(WishlistTable)
    df_wishlist = pd.read_sql(stmt, con=db)

    stmt = select("*").select_from(SizeTable)
    df_size = pd.read_sql(stmt, con=db)

    stmt = select(
        [
            wishlist_product_association.c.wishlist_id,
            wishlist_product_association.c.product_id,
        ]
    )
    df_wishlist_product = pd.read_sql(stmt, con=db)

    stmt = select(
        [
            customer_product_association.c.customer_id,
            customer_product_association.c.product_id,
            customer_product_association.c.order_date,
        ]
    )
    df_customer_product = pd.read_sql(stmt, con=db)

    # 2: rename index column and fix datetime format
    df_customer.rename(columns={"customer_id": "_id"}, inplace=True)
    # df_address.rename(columns={"address_id": "_id"}, inplace=True)
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
    df_cart["payment_date"] = pd.to_datetime(df_cart["payment_date"])
    df_customer_product["order_date"] = pd.to_datetime(df_cart["order_date"])

    # 3: create Customer Collection in mongodb and embed Address
    customer_col = mongo_db["customer"]
    customer_col.create_index([("_id", pymongo.ASCENDING)], unique=True)

    # merge Customer and Address dataframes to embed address:
    df_merged = pd.merge(df_customer, df_address, on="address_id", how="left")

    # drop the address id column from the merged dataframe:
    df_merged.drop("address_id", axis=1, inplace=True)

    # convert the merged dataframe to a list of dicts and insert into mongdb
    # customers = [row.dropna().to_dict() for _, row in df_customer.iterrows()]
    customers = df_merged.to_dict(orient="records")

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
                df_wishlist_product["wishlist_id"] == wishlist_id
            ]["product_id"].toList()

            wishlist["product_ids"] = wishlist_product_ids

        customer["wishlists"] = wishlists

    # REFERENCING TO ORDERS IDs

    customer_col.insert_many(customers)

    # 4: create Product Collection in mongodb and embed Category
    # Merge Product and Category dataframes to embed category info within product:
    df_merged = pd.merge(df_product, df_category, on="_id", how="left")

    # create Product Collection in mongodb
    product_col = mongo_db["product"]  # OR: product_collection = mongo_db.db.product

    # Indexing:
    product_col.create_index([("_id", pymongo.ASCENDING)], unique=True)
    product_col.create_index([("category._id", pymongo.ASCENDING)])

    # products = [row.dropna().to_dict() for _, row in df_product.iterrows()]
    # col.insert_many(products)

    # Convert the merged dataframe to a list of dictionaries and insert into MongoDB
    products = df_merged.to_dict(orient="records")
    product_col.insert_many(products)

    # 5: create Cart Collection in mongodb and embed Payment and reference to customer_id
    # Merge Cart and Payment dataframes to embed payment info within cart:
    df_merged = pd.merge(df_cart, df_payment, on="_id", how="left")

    # create Cart Collection in mongodb
    cart_col = mongo_db["cart"]  # OR: product_collection = mongo_db.db.product

    # Indexing:
    cart_col.create_index(
        [
            ("customer_id", pymongo.ASCENDING),
            ("status", pymongo.ASCENDING),
            ("_id", pymongo.ASCENDING),
        ],
        unique=True,
    )

    # Convert the merged dataframe to a list of dictionaries and insert into MongoDB
    carts = df_merged.to_dict(orient="records")

    # Embed CartItems within each Cart document:
    for cart in carts:
        cart_id = cart["_id"]
        cartitems = df_cartitem[df_cartitem["cart_id"] == cart_id].to_dict(
            orient="records"
        )
        cart["cart_items"] = cartitems

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
    order_col = mongo_db["order"]
