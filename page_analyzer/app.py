from flask import (Flask,
                   render_template,
                   request,
                   url_for,
                   redirect,
                   flash,
                   get_flashed_messages)
import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path
import validators
from urllib.parse import urlparse
import datetime
import requests
from .html import get_info_about_site


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env"))


def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))


def select_from_db(*args, fetch='one'):
    conn = get_conn()
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
    conn = get_conn()
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


def normalize_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme + '://' + parsed_url.netloc


app = Flask(__name__)


app.secret_key = os.getenv("SECRET_KEY")

conn = get_conn()
# create a cursor
cur = conn.cursor()

cur.execute(
    '''CREATE TABLE IF NOT EXISTS urls (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name       varchar(255) UNIQUE,
    created_at timestamp
);''')

cur.execute(
    '''CREATE TABLE IF NOT EXISTS url_checks (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    url_id bigint REFERENCES urls(id),
    status_code integer,
    h1 text,
    title text,
    description text,
    created_at timestamp
);''')
conn.commit()
cur.close()
conn.close()


@app.route('/')
def index():
    messages = get_flashed_messages(with_categories=True)
    return render_template('index.html', messages=messages)


@app.route('/urls', methods=('GET', 'POST'))
def urls():
    if request.method == 'POST':
        url = request.form.get('url')
        if validators.url(url) and validators.length(url, max=255):
            normalized_url = normalize_url(url)
            try:
                data = insert_to_db('''
                            INSERT INTO urls(name, created_at)
                            VALUES (%s, %s)
                            RETURNING id;
                            ''',
                            (normalized_url, datetime.datetime.now()))
                id = data[0]
                flash('Страница успешно добавлена', 'info')
                return redirect(url_for('url', id=id))
            except psycopg2.errors.UniqueViolation:
                data = select_from_db('SELECT id FROM urls WHERE name = %s;',
                                      (normalized_url,))
                id = data[0]
                flash('Страница уже существует', 'info')
                return redirect(url_for('url', id=id))
        flash('Некорректный URL', 'danger')
        messages = get_flashed_messages(with_categories=True)
        return render_template('index.html',
                               url=url_for('index'),
                               messages=messages), 422
    if request.method == 'GET':
        sites = select_from_db('SELECT * FROM urls ORDER BY id DESC;', fetch='all')
        checks = select_from_db('''
                                SELECT DISTINCT ON (url_id) created_at, status_code
                                FROM url_checks
                                ORDER BY url_id DESC, created_at DESC;
                                ''', fetch='all')
        return render_template('urls.html', sites=sites, checks=checks)


@app.route('/urls/<id>', methods=('GET',))
def url(id):
    messages = get_flashed_messages(with_categories=True)
    data = select_from_db('SELECT * FROM urls WHERE id = %s;', (id,))
    site = data
    checks = select_from_db('''
                            SELECT * FROM url_checks
                            WHERE url_id = %s
                            ORDER BY id DESC;
                            ''',
                            (id,),
                            fetch='all')
    return render_template('url_detail.html',
                           site=site,
                           checks=checks,
                           messages=messages)


@app.route('/urls/<id>/checks', methods=('POST',))
def url_check(id):
    data = select_from_db('SELECT name FROM urls WHERE id = %s;', (id,))
    url = data[0]
    try:
        data = get_info_about_site(url, id)
        insert_to_db('''
                     INSERT INTO url_checks
                     (url_id, status_code, h1, title, description, created_at)
                     VALUES (%s, %s, %s, %s, %s, %s);
                     ''',
                     data)
        flash('Страница успешно проверена', 'success')
        return redirect(url_for('url', id=id))
    except requests.exceptions.RequestException as e:
        flash('Произошла ошибка при проверке', 'danger')
        return redirect(url_for('url', id=id))
