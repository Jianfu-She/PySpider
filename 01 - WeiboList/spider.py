from urllib.parse import urlencode
from pyquery import PyQuery as pq

import requests

base_url = 'https://m.weibo.cn/api/container/getIndex?'

headers = {
    'host': 'm.weibo.cn',
    'Referer': 'https://m.weibo.cn/u/5757189292',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/58.0.3029.110 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}

weibo = {}


def get_page(page):
    params = {
        'containerid': '1076035757189292',
        'page': page
    }
    url = base_url + urlencode(params)
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
    except requests.ConnectionError as e:
        print('Error', e.args)


def parse_page(json):
    if json:
        items = json.get('data').get('cards')
        for item in items:
            mblog = item.get('mblog')
            weibo['id'] = mblog.get('id')
            weibo['text'] = pq(mblog.get('text')).text()
            weibo['attitudes'] = mblog.get('attitudes_count')
            weibo['comments'] = mblog.get('comments_count')
            weibo['reports'] = mblog.get('reposts_count')
            weibo['source'] = mblog.get('source')
            yield weibo


if __name__ == '__main__':
    for page in range(1, 6):
        json = get_page(page)
        results = parse_page(json)
        for result in results:
            print(result)
