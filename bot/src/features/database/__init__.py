from os import getenv
from mysql.connector import connect

def get_connection():
    conn = connect(
        host=getenv("DB_HOST"),
        user=getenv("DB_USER"),
        password=getenv("DB_PASSWORD"),
        database=getenv("DB_NAME")
    )

    return conn
