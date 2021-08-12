import os
import requests as req
import time

import telebot
from bs4 import BeautifulSoup

url = os.environ.get('URL')
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0'}
timeout = 5
check_interval = int(os.environ.get('CHECK_INTERVAL'))

token = os.environ.get('TOKEN')
chat_id = os.environ.get('CHAT_ID')

last_date_modified = ''
last_page_text = ''


def main():
    bot = telebot.TeleBot(token)

    while True:
        try:
            page = get_page()
            result = check_data(page)
            if result is not None:
                if isinstance(result, list):
                    result = '\n'.join(result)
                result = 'Text has been changed:\n' + result
                bot.send_message(chat_id, result)
                print(result)

        except Exception as e:
            print(e)

        time.sleep(check_interval)


def get_page():
    r = req.get(url, headers=headers, timeout=timeout)
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, "html.parser")
        return soup.find('div', {'class': 'part2-item'})
    else:
        return None


def get_date_modified(page_text):
    return page_text.find('span', {'class': 'itemDateModified'}).string.strip()


def check_data(page):
    global last_date_modified, last_page_text

    if page is not None:
        date_modified = get_date_modified(page)

        if last_date_modified != date_modified:
            last_date_modified = date_modified

            if last_page_text == '':
                last_page_text = page.text
            else:
                result = compare_text(last_page_text, page.text)
                last_page_text = page.text
                return result
    return None


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

        return result

    except Exception as e:
        return str(e)


if __name__ == '__main__':
    main()
