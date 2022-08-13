import psycopg2
import requests as req
import hashlib
from bs4 import BeautifulSoup
import os
import time
import telebot

check_interval = int(os.environ.get('CHECK_INTERVAL'))
token = os.environ.get('TOKEN')
chat_id = os.environ.get('CHAT_ID')
db_name = os.environ.get('DB_NAME')
db_user = os.environ.get('DB_USER')
db_pass = os.environ.get('DB_PASS')
db_host = os.environ.get('DB_HOST')

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0'}
timeout = 5

PAGE_ID = 0
PAGE_URL = 1
PAGE_HASH = 2
PAGE_SELECTOR = 3
PAGE_CURRENT_TEXT = 4
PAGE_PREVIOUS_TEXT = 5


def main():
    bot = telebot.TeleBot(token)
    while True:
        connection = get_db_connection()
        cursor = connection.cursor()
        page_info = get_db_page_info(cursor)
        for info in page_info:
            try:
                page = get_page(info)
                if not info[PAGE_HASH] or not info[PAGE_CURRENT_TEXT]:
                    update_db_page_info(cursor, page, info)
                else:
                    changes = compare_pages(page, info)
                    if changes:
                        update_db_page_info(cursor, page, info)
                        send_changes(bot, info, changes)
            except Exception as e:
                print(e)
        connection.commit()
        cursor.close()
        connection.close()
        time.sleep(check_interval)


def get_db_connection():
    connection = psycopg2.connect(dbname=db_name, user=db_user, password=db_pass, host=db_host)
    return connection


def get_db_page_info(cursor):
    cursor.execute(
        'SELECT page_id, page_url, page_hash, page_selector, page_current_text, page_previous_text FROM page'
    )
    return cursor.fetchall()


def update_db_page_info(cursor, page, info):
    cursor.execute('UPDATE page SET page_hash=%s, page_current_text=%s, page_previous_text=%s WHERE page_id=%s',
                   (get_hash(page), str(page), info[PAGE_CURRENT_TEXT], info[PAGE_ID]))


def get_page(info):
    result = req.get(info[PAGE_URL], headers=headers, timeout=timeout)
    if result.status_code == req.codes.ok:
        soup = BeautifulSoup(result.text, "html.parser")
        page = soup.select(info[PAGE_SELECTOR])
        page = '\n'.join([str(item) for item in page])
        return page
    else:
        raise ConnectionError("Response code: ", result.status_code)


def compare_pages(page, info):
    if get_hash(page) != info[PAGE_HASH]:
        if page != info[PAGE_CURRENT_TEXT]:
            page_text = BeautifulSoup(page, "html.parser").text
            info_text = BeautifulSoup(info[PAGE_CURRENT_TEXT], "html.parser").text
            return get_changes(info_text, page_text)
    return None


def get_hash(data):
    hash_object = hashlib.sha1(data.encode())
    return hash_object.hexdigest()


def get_changes(old_text, new_text):
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

        if result and isinstance(result, list):
            result = '\n'.join(result)

        return result

    except Exception as e:
        return str(e)


def send_changes(bot, info, changes):
    max_length = 4096
    changes = f"Text has been changed on {info[PAGE_URL]} :\n{changes}"
    start = 0
    while start < len(changes):
        end = start + max_length
        if end > len(changes):
            end = len(changes)
        bot.send_message(chat_id, changes[start:end])
        start = end
    print(changes)


if __name__ == '__main__':
    main()
