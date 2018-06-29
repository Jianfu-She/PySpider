from requests import Session
from weixin.config import *
from weixin.db import RedisQueue
from weixin.mysql import MySQL
from weixin.request import WeixinRequest
from urllib.parse import urlencode
import requests
from pyquery import PyQuery as pq
from requests import ReadTimeout, ConnectionError


class Spider(object):
    base_url = 'http://weixin.sogou.com/weixin'
    keyword = 'NBA'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,ja;q=0.4,zh-TW;q=0.2,mt;q=0.2',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Cookie': 'SUV=0019178D7139E4CF5A98E24886E85289; SUID=9AF49C733120910A000000005AAA1750; ABTEST=8|1530090681|v'
                  '1;IPLOC=CN4210; weixinIndexVisited=1; SNUID=612CF6BECECAA052EA3A6F50CF791601; JSESSIONID=aaa0_Q-S5EK'
                  '7BcKF4S7qw; ppinf=5|1530098114|1531307714|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZToyNzolRTQlQk'
                  'QlOTglRTUlODElQTUlRTUlQTQlQUJ8Y3J0OjEwOjE1MzAwOTgxMTR8cmVmbmljazoyNzolRTQlQkQlOTglRTUlODElQTUlRTUlQT'
                  'QlQUJ8dXNlcmlkOjQ0Om85dDJsdU9JbjdQV1F4UC1wQV90UDhDR2dLdE1Ad2VpeGluLnNvaHUuY29tfA; pprdig=RnSWD7qnomx'
                  'sf-V3yOXjt7Jk9zZwYYiXZKsByre9tciFYGNqAreHjU1paH2_7j9yUJDAxxdJZ4rfTI8EwIRhK_rDckoa0PcwrKB2UzA2ou--Ddl'
                  'KELNDgr-2EOPJ5BdDFBgJh84r7fsZC2SQBEGzB0kqxVboX6ZzSXdGS86hlRE; sgid=23-35736769-AVszccJNic84GSkZY3bek'
                  'BMY; ppmdig=15300981140000009a7459d5a937b96a96b9db16b616914a; sct=3',
        'Host': 'weixin.sogou.com',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/59.0.3071.115 Safari/537.36'
    }
    session = Session()
    queue = RedisQueue()
    mysql = MySQL()

    def get_proxy(self):
        """
        从代理池获取代理
        :return:
        """
        try:
            response = requests.get(PROXY_POOL_URL)
            if response.status_code == 200:
                print('Get Proxy', response.text)
                return response.text
            return None
        except requests.ConnectionError:
            return None

    def start(self):
        """
        初始化
        :return:
        """
        # 全局更新headers
        self.session.headers.update(self.headers)
        start_url = self.base_url + '?' + urlencode({'query': self.keyword, 'type': 2})
        weixin_request = WeixinRequest(url=start_url, callback=self.parse_index, need_proxy=True)
        # 调度第一个请求
        self.queue.add(weixin_request)

    def parse_index(self, response):
        """
        解析索引页
        :param response:
        :return:
        """
        doc = pq(response.text)
        items = doc('.news-box .news-list li .txt-box h3 a').items()
        for item in items:
            url = item.attr('href')
            weixin_request = WeixinRequest(url=url, callback=self.parse_detail)
            yield weixin_request
        next = doc('#sogou_next').attr('href')
        if next:
            url = self.base_url + str(next)
            weixin_request = WeixinRequest(url=url, callback=self.parse_index, need_proxy=True)
            yield weixin_request

    def parse_detail(self, response):
        """
        解析详情页
        :param response:
        :return: 微信公众号文章
        """
        doc = pq(response.text)
        data = {
            'title': doc('.rich_media_title').text(),
            'content': doc('.rich_media_content').text(),
            'data': doc('#post-data').text(),
            'nickname': doc('#js_profile_qrcode > div > strong').text(),
            'wechat': doc('#js_profile_qrcode > div > p:nth-child(3) > span').text()
        }
        yield data

    def request(self, weixin_request):
        """
        执行请求
        :param weixin_request:
        :return:
        """
        try:
            if weixin_request.need_proxy:
                proxy = self.get_proxy()
                if proxy:
                    proxies = {
                        'http': 'http://' + proxy,
                        'https': 'https://' + proxy
                    }
                    return self.session.send(weixin_request.prepare(), timeout=weixin_request.timeout,
                                             allow_redirects=False, proxies=proxies)
            return self.session.send(weixin_request.prepare(), timeout=weixin_request.timeout, allow_redirects=False)
        except(ConnectionError, ReadTimeout) as e:
            print(e.args)
            return False

    def error(self, weixin_request):
        """
        错误处理
        :param weixin_request:
        :return:
        """
        weixin_request.fail_time = weixin_request.fail_time + 1
        print('Request Failed', weixin_request.fail_time, 'Times', weixin_request.url)
        if weixin_request.fail_time < MAX_FAILED_TIME:
            self.queue.add(weixin_request)

    def schedule(self):
        """
        调度请求
        :return:
        """
        while not self.queue.empty():
            weixin_request = self.queue.pop()
            callback = weixin_request.callback
            print('Schedule', weixin_request.url)
            response = self.request(weixin_request)
            if response and response.status_code in VALID_STATUSES:
                results = list(callback(response))
                if results:
                    for result in results:
                        print('New Result', type(result))
                        if isinstance(result, WeixinRequest):
                            self.queue.add(result)
                        if isinstance(result, dict):
                            self.mysql.insert('articles', result)
                else:
                    self.error(weixin_request)
            else:
                self.error(weixin_request)

    def run(self):
        self.start()
        self.schedule()