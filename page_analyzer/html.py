import requests
from bs4 import BeautifulSoup
import datetime


def has_descriptions(tag):
    return tag.get('name') == 'description'


def get_info_about_site(url, id):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html.parser')
    h1 = soup.h1.get_text() if soup.h1 else ''
    title = soup.title.get_text() if soup.title else ''
    if soup.find_all(has_descriptions):
        description = soup.find_all(has_descriptions)[0].get('content')
    else:
        description = ''
    created_at = datetime.datetime.now()
    return id, r.status_code, h1, title, description, created_at
