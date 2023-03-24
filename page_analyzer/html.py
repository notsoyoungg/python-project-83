import requests
from bs4 import BeautifulSoup
import datetime


def get_page_seo_data(url):
    r = requests.get(url)
    r.raise_for_status()
    data = {}
    data['status_code'] = r.status_code
    soup = BeautifulSoup(r.content, 'html.parser')
    data['h1'] = soup.h1.get_text() if soup.h1 else ''
    data['title'] = soup.title.get_text() if soup.title else ''
    meta = soup.find('meta', attrs={'name': 'description'})
    data['description'] = ''
    if meta:
        data['description'] = soup.find('meta',
                                        attrs={'name': 'description'}
                                        ).get('content')
    data['created_at'] = datetime.datetime.now()
    return data
