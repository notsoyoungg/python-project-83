import requests
from bs4 import BeautifulSoup


def get_info_about_site(url):
    r = requests.get(url)
    data = {}
    data['status_code'] = r.status_code
    soup = BeautifulSoup(r.content, 'html.parser')
    if soup.h1:
        data['h1'] = soup.h1.get_text()
    if soup.title:
        data['title'] = soup.title.get_text()
    for meta in soup.find_all('meta'):
        if meta.get('name') == 'description':
            data['description'] = meta.get('content')
    return data

# print(r.text)

def func(*args):
    print(*args)

func(1, 5, 6)
print([None] * 5)
# except requests.exceptions.RequestException as e:
#     print(f'вылетело исключение {e}')
print(len('Живое онлайн сообщество программистов и разработчиков на JS, Python, Java, PHP, Ruby. Авторские программы обучения с практикой и готовыми проектами в резюме. Помощь в трудоустройстве после'))
print(len([[]]))