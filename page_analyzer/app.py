from flask import (Flask,
                   render_template,
                   request,
                   url_for,
                   redirect,
                   flash)
import psycopg2
from psycopg2.extras import DictCursor
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


def normalize_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme + '://' + parsed_url.netloc


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


@app.route('/')
def index():
    return render_template('index.html')


@app.get('/urls')
def urls_get():
    with psycopg2.connect(os.getenv("DATABASE_URL"),
                          cursor_factory=DictCursor) as conn:
        with conn.cursor() as curs:
            curs.execute('''
                         SELECT distinct on (urls.id)
                         urls.id,
                         urls.name,
                         url_checks.created_at,
                         url_checks.status_code
                         FROM urls LEFT JOIN url_checks
                         ON urls.id=url_checks.url_id
                         ORDER BY urls.id DESC, created_at desc;
                         ''')
            sites = curs.fetchall()
    return render_template('urls.html', sites=sites)


@app.post('/urls')
def urls_post():
    url = request.form.get('url')
    if validators.url(url) and validators.length(url, max=255):
        normalized_url = normalize_url(url)
        with psycopg2.connect(os.getenv("DATABASE_URL"),
                              cursor_factory=DictCursor) as conn:
            with conn.cursor() as curs:
                try:
                    curs.execute('''
                                 INSERT INTO urls(name, created_at)
                                 VALUES (%s, %s)
                                 RETURNING id;
                                 ''',
                                 (normalized_url, datetime.datetime.now()))
                    id = curs.fetchone()['id']
                    flash('Страница успешно добавлена', 'info')
                    return redirect(url_for('url', id=id))
                except psycopg2.errors.UniqueViolation:
                    curs.execute('SELECT id FROM urls WHERE name = %s;',
                                 (normalized_url,))
                    id = curs.fetchone()['id']
                    flash('Страница уже существует', 'info')
                    return redirect(url_for('url', id=id))
    flash('Некорректный URL', 'danger')
    return render_template('index.html',
                           url=url_for('index')), 422


@app.route('/urls/<id>', methods=('GET',))
def url(id):
    with psycopg2.connect(os.getenv("DATABASE_URL"),
                          cursor_factory=DictCursor) as conn:
        with conn.cursor() as curs:
            curs.execute('SELECT * FROM urls WHERE id = %s;', (id,))
            site = curs.fetchone()
            curs.execute('''
                         SELECT * FROM url_checks
                         WHERE url_id = %s
                         ORDER BY id DESC;
                         ''',
                         (id,))
            checks = curs.fetchall()
    return render_template('url_detail.html',
                           site=site,
                           checks=checks)


@app.route('/urls/<id>/checks', methods=('POST',))
def url_check(id):
    with psycopg2.connect(os.getenv("DATABASE_URL"),
                          cursor_factory=DictCursor) as conn:
        with conn.cursor() as curs:
            curs.execute('SELECT name FROM urls WHERE id = %s;', (id,))
            url = curs.fetchone()['name']
            try:
                data = get_info_about_site(url, id)
                curs.execute('''
                             INSERT INTO url_checks
                             (url_id, status_code, h1,
                             title, description, created_at)
                             VALUES (%s, %s, %s, %s, %s, %s);
                             ''',
                             data)
                flash('Страница успешно проверена', 'success')
                return redirect(url_for('url', id=id))
            except requests.exceptions.RequestException:
                flash('Произошла ошибка при проверке', 'danger')
                return redirect(url_for('url', id=id))
