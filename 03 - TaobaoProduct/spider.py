from urllib.parse import quote

import pymysql
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from pyquery import PyQuery as pq

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
browser = webdriver.Chrome(chrome_options=chrome_options)
wait = WebDriverWait(browser, 10)
KEYWORD = 'iPad'


def index_page(page):
    print('正在爬取第', page, '页')
    try:
        url = 'https://s.taobao.com/search?q=' + quote(KEYWORD)
        browser.get(url)
        if page > 1:
            input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#mainsrp-pager div.form > input'))
            )
            submit = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '#mainsrp-pager div.form > span.btn.J_Submit'))
            )
            input.clear()
            input.send_keys(page)
            submit.click()
        wait.until(
            EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#mainsrp-pager li.item.active > span'), str(page))
        )
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.m-itemlist .items .item')))
        get_products()
    except TimeoutException:
        index_page(page)


def get_products():
    html = browser.page_source
    doc = pq(html)
    items = doc('.m-itemlist .items .item').items()
    for item in items:
        product = {
            'image': item.find('.pic .img').attr('data-src'),
            'price': item.find('.price').text().replace('¥\n', ''),
            'deal': item.find('.deal-cnt').text()[:-3],
            'title': item.find('.title').text().replace('\n', ''),
            'shop': item.find('.shop').text(),
            'location': item.find('.location').text()
        }
        print(product)
        save_to_mysql(product)


def save_to_mysql(product):
    db = pymysql.connect(host='localhost', user='root', password='password', port=3306, db='customs', charset='utf8')
    cursor = db.cursor()
    sql = 'INSERT INTO t_product(image, price, deal, title, shop, location) VALUES (%s, %s, %s, %s, %s, %s)'
    try:
        cursor.execute(sql, (product.get('image'), product.get('price'), product.get('deal'),
                             product.get('title'), product.get('shop'), product.get('location')))
        db.commit()
    except Exception as e:
        db.rollback()
        print('MySql写入失败', e.args)
    db.close()


def main():
    for i in range(1, 6):
        index_page(i)


if __name__ == '__main__':
    main()
