import os
import re
import requests as req
import time
import telebot
from bs4 import BeautifulSoup

urls = os.environ.get('URLS')
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0'}
timeout = 5
check_interval = int(os.environ.get('CHECK_INTERVAL'))

token = os.environ.get('TOKEN')
chat_id = os.environ.get('CHAT_ID')


def main():
    bot = telebot.TeleBot(token)
    url_list = urls.split(";")
    last_data = list()
    for url in url_list:
        last_data.append({'url': url, 'text': '', 'date': ''})

    while True:
        for data in last_data:
            try:
                page = get_page(data['url'])
                result, data['text'], data['date'] = check_data(page, data['text'], data['date'])
                if result is not None:
                    if isinstance(result, list):
                        result = '\n'.join(result)
                    result = 'Text has been changed on ' + data['url'] + ' :\n' + result
                    bot.send_message(chat_id, result)
                    print(result)

            except Exception as e:
                print(e)

        time.sleep(check_interval)


def get_page(url):
    r = req.get(url, headers=headers, timeout=timeout)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        page = soup.find('div', {'class': 'part2-item'})
        if page is not None:
            return page

        regex = re.compile('"<div class=\'ballon-point\'>.+?"')
        page = regex.findall(r.text)
        page = '\n'.join(page)
        return BeautifulSoup(page, "html.parser")
    else:
        return None


def get_date_modified(page_text):
    result = page_text.find('span', {'class': 'itemDateModified'})
    if result is not None:
        return result.string.strip()
    else:
        return None


def check_data(page, last_page_text, last_date_modified):
    if page is not None:
        date_modified = get_date_modified(page)

        if last_date_modified != date_modified or date_modified is None:
            last_date_modified = date_modified

            if last_page_text == '':
                last_page_text = page.text
            else:
                result = compare_text(last_page_text, page.text)
                last_page_text = page.text
                return [result, last_page_text, last_date_modified]
    return [None, last_page_text, last_date_modified]


def compare_text(old_text, new_text):
    try:
        new_text = new_text.split('\n')
        old_text = old_text.split('\n')
        result = list()

        for n in new_text:
            for o in old_text:
                if n == o:
                    result.append(n)
                    old_text.remove(o)
                    break
        for f in result:
            new_text.remove(f)

        result.clear()

        for o in old_text:
            result.append(f'- {o}')
        for n in new_text:
            result.append(f'+ {n}')

        if not result:  # пуст
            return None
        else:
            return result

    except Exception as e:
        return str(e)


if __name__ == '__main__':
    main()
