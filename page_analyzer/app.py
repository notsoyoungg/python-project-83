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
from .db import select_from_db, insert_to_db


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env"))


def normalize_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme + '://' + parsed_url.netloc


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


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
        sites = select_from_db('''
                               SELECT distinct on (urls.id)
                               urls.id,
                               urls.name,
                               url_checks.created_at,
                               url_checks.status_code
                               FROM urls LEFT JOIN url_checks
                               ON urls.id=url_checks.url_id
                               ORDER BY urls.id DESC, created_at desc;
                               ''',
                               fetch='all')
        return render_template('urls.html', sites=sites)


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
    except requests.exceptions.RequestException:
        flash('Произошла ошибка при проверке', 'danger')
        return redirect(url_for('url', id=id))
