from lxml import html
import re
import requests
import datetime
import time
import vk_api
from config import *

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0'
}

image_query = """
//a[
    @class='image'
]/img[
    (@class = 'thumbimage' or @elementtiming[
        contains(.,'thumbnail')
    ]) or @width >= 100 and 
    @height >= 100 and 
    not(@src[
        contains(.,'.svg')
    ])
]"""
description_query = """
//div[
    @class='mw-parser-output'
]/*[
    (self::p or self::ul) and 
    (count(preceding-sibling::h2) = 0 or following-sibling::h2 and 
    count(preceding-sibling::h2) = 1 and 
    count(preceding-sibling::div[
        @id = 'toc' and 
        count(preceding-sibling::p) = 0
    ])=1)
]
"""
random_page_link = 'https://ru.wikipedia.org/wiki/Служебная:Случайная_страница'
api = None


def upload_photo(photo_url):
    # Получаем данные для загрузки
    upload_url = api.method('photos.getUploadServer', {'album_id': album_id, 'group_id': group_id})['upload_url']
    # Скачиваем фото
    image = requests.get(photo_url, headers=headers).content
    with open('page_pic.jpg', 'wb') as handler:
        handler.write(image)

    # Получаем фото
    files = {'photo': open('page_pic.jpg', 'rb')}

    # Загружаем фото на сервер
    response_data = requests.post(upload_url, files=files).json()
    try:
        # Сохраняем фото в альбом
        photo_info = api.method('photos.save', {
                                    'group_id': group_id,
                                    'album_id': album_id,
                                    'server': response_data['server'],
                                    'photos_list': response_data['photos_list'],
                                    'aid': response_data['aid'],
                                    'hash': response_data['hash']
                                })[0]
        return photo_info
    except vk_api.exceptions.ApiError as err:
        print(err)
        return None


# Авторизация вк
try:
    if 'login' in globals() and 'password' in globals():
        api = vk_api.VkApi(login, password, auth_handler = lambda: input('Введите код двуфакторной аутентификации: '), api_version = '5.103')
    elif 'token' in globals():
        api = vk_api.VkApi(token=token)
    else:
        print('Error. No credentials');
    api.auth(token_only=True)
except vk_api.AuthError as error_msg:
    print(error_msg)

# Получаем текущие минуты
minutes = datetime.datetime.now().minute

# Если время не ровное, ждём ровного
if minutes > 30 and nice_time:
    print(f'Ждём {61 - minutes} минут до круглого времени')
    time.sleep((61 - minutes) * 60)
elif minutes < 30 and minutes not in range(0, 3) and nice_time:
    print(f'Ждём {30 - minutes} минут до круглого времени')
    time.sleep((30 - minutes) * 60)
i=1
# Основной цикл программы
while i > 0:
    # Обнуляем переменные
    description = ''
    att = None
    atts = ''

    # Получаем случайную статью на вики
    resp = requests.get(random_page_link)
    wiki_html_str = resp.text
    wiki_html = html.fromstring(wiki_html_str)

    # Получаем изображение статьи
    img = wiki_html.xpath(image_query)

    # Загружаем фото статьи в альбом группы
    if img.__len__() > 0 and only_pic:
        img_url = 'https:' + re.sub(r'/\d+px(.)+', '', img[0].attrib['src'].replace('/thumb', ''))
        att = upload_photo(img_url)
    else:
        continue

    # Запоминаем url статьи
    url = resp.url

    # Запоминаем заголовок
    title = wiki_html.get_element_by_id('firstHeading').text_content()

    # Получаем краткое описание статьи
    p_list = wiki_html.xpath(description_query)
    for p in p_list:
        description += re.sub(r'\[\S+\]', '', p.text_content()) + '\n'

    if att != None:
        atts = f"photo{att['owner_id']}_{att['id']}"
    atts += ',' + url

    # Постим
    api.method('wall.post',
               {
                   'owner_id': -group_id,
                   'from_group': 1,
                   'message': f'{title}\n\n{description}\n\n{url}',
                   'attachments': atts,
                   'copyright': url
               })
    print(
        f"Запись про {title} успешно опубликована в "
        f"{datetime.datetime.strftime(datetime.datetime.now(), '%H:%M (%a %d.%m)')}")
    time.sleep(i)
    i-=1
