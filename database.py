import sqlite3
from flask import g  

def connect_to_database():
    sql = sqlite3.connect("/home/dion/tflask/tech.db")
    sql.row_factory = sqlite3.Row
    return sql

def get_database():
    if not hasattr(g, 'tech_db'):
        g.tech_db = connect_to_database()
    return g.tech_db
