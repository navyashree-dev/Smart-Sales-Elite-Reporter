import sqlite3
import pandas as pd 
def save_to_db(df):
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

    conn = sqlite3.connect("data/transactions.db")
    df.to_sql("transactions", conn, if_exists="replace", index=False)
    conn.close()