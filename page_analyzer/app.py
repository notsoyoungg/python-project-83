from flask import Flask, render_template, request, url_for, redirect, flash, get_flashed_messages
import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path
import validators
from urllib.parse import urlparse
import datetime
import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env"))

def get_data_from_db(*args):
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    data = []
    for arg in args:
        if isinstance(arg, tuple):
            cur.execute(*arg)
            data.append(cur.fetchall())
        else:
            cur.execute(arg)
            data.append(cur.fetchall())
    conn.commit()
    cur.close()
    conn.close()
    return data

def insert_data_to_db(query, params):
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    cur.close()
    conn.close()


def normalize_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme + '://' + parsed_url.netloc

def get_info_about_site(url, id):
    r = requests.get(url)
    data = [None] * 6
    data[0] = id
    data[1] = r.status_code
    soup = BeautifulSoup(r.content, 'html.parser')
    if soup.h1:
        data[2] = soup.h1.get_text()
    if soup.title:
        data[3] = soup.title.get_text()
    for meta in soup.find_all('meta'):
        if meta.get('name') == 'description':
            data[4] = meta.get('content')
    data[5] = datetime.datetime.now()
    return data


app = Flask(__name__)


app.secret_key = os.getenv("SECRET_KEY")

# Connect to the database
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
  
# create a cursor
cur = conn.cursor()

cur.execute(
    '''CREATE TABLE IF NOT EXISTS urls (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    name       varchar(255),
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
  
# commit the changes
conn.commit()
  
# close the cursor and connection
cur.close()
conn.close()

@app.route('/')
def index():
    messages = get_flashed_messages(with_categories=True)
    return render_template('index.html', messages=messages)

@app.route('/urls', methods=('GET', 'POST'))
def urls():
    if request.method == 'POST':
        url = request.form['url']
        if validators.url(url) and validators.length(url, max=255):
            normalized_url = normalize_url(url)
            name = get_data_from_db(('SELECT id, name FROM urls WHERE name = %s', (normalized_url,)))
            print(name)
            print(name[0])
            # print(name[0][1])
            if len(name[0]) != 0 and name[0][0][1] == normalized_url:
                flash('Страница уже существует', 'info')
                return redirect(url_for('url', id=name[0][0][0]))
            insert_data_to_db('INSERT INTO urls (name, created_at) VALUES (%s, %s)',
                        (normalized_url, datetime.datetime.now()))
            flash('Страница спешно добавлена', 'info')
            return redirect(url_for('index'))
        flash('Некорректный URL', 'danger')
        return redirect(url_for('index'))
    if request.method == 'GET':
        data = get_data_from_db(('SELECT * FROM urls ORDER BY id DESC;'),
                                  ('SELECT DISTINCT ON (url_id) created_at, status_code FROM url_checks ORDER BY url_id DESC, created_at DESC;'))
        return render_template('urls.html', sites=data[0], checks=data[1])
    
@app.route('/urls/<id>', methods=('GET', 'POST'))
def url(id):
    messages = get_flashed_messages(with_categories=True)
    data = get_data_from_db(('SELECT * FROM urls WHERE id = %s;', (id,)),
                                    ('SELECT * FROM url_checks WHERE url_id = %s ORDER BY id DESC;', (id,)))
    return render_template('url_detail.html', site=data[0], checks=data[1], messages=messages)

@app.route('/urls/<id>/checks', methods=('POST',))
def url_check(id):
    data = get_data_from_db(('SELECT name FROM urls WHERE id = %s;', (id,)),)
    print(data)
    url = data[0][0][0]
    print(url)
    try:
        data = get_info_about_site(url, id)
        insert_data_to_db('INSERT INTO url_checks (url_id, status_code, h1, title, description, created_at) VALUES (%s, %s, %s, %s, %s, %s)', data)
        flash('Страница успешно проверена', 'success')
        return redirect(url_for('url', id=id))
    except requests.exceptions.RequestException as e:
        print(e)
        flash('Произошла ошибка при проверке', 'danger')
        return redirect(url_for('url', id=id))
