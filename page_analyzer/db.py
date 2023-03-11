import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env"))


def select_from_db(*args, fetch='one'):
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute(*args)
    if fetch != 'one':
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    data = cur.fetchone()
    cur.close()
    conn.close()
    return data


def insert_to_db(query, params):
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute(query, params)
    try:
        data = cur.fetchone()
    except psycopg2.ProgrammingError:
        data = ()
    conn.commit()
    cur.close()
    conn.close()
    return data
