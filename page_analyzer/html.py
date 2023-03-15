import requests
from bs4 import BeautifulSoup
import datetime


def get_info_about_site(url, id):
    r = requests.get(url)
    r.raise_for_status()
    data = {}
    data['id'] = id
    data['status_code'] = r.status_code
    soup = BeautifulSoup(r.content, 'html.parser')
    data['h1'] = soup.h1.get_text() if soup.h1 else ''
    data['title'] = soup.title.get_text() if soup.title else ''
    if soup.find('meta', attrs={'name': 'description'}):
        data['description'] = soup.find('meta',
                                        attrs={'name': 'description'}
                                        ).get('content')
    else:
        data['description'] = ''
    data['created_at'] = datetime.datetime.now()
    return data
