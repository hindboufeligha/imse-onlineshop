import pymongo
import pandas as pd
from lib.init_database_functions import *
from sqlalchemy import select


def migrate_all_data(db, mongo_db):
    # fetch all customers:
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

    # rename index column and fix datetime format
    df_customer.rename(columns={"customer_id": "_id"}, inplace=True)
    df_address.rename(columns={"address_id": "_id"}, inplace=True)
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

    # df_address.drop("address_id", axis=1, inplace=True)   #LATER

    # create customer collection
    col = mongo_db["customer"]
    col.create_index([("_id", pymongo.ASCENDING)], unique=True)
    col.create_index([("username", pymongo.ASCENDING)], unique=True)
    users = [row.dropna().to_dict() for _, row in df_customer.iterrows()]
    col.insert_many(users)

    
