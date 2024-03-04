import requests
import time
import random
from datetime import datetime
import os
import csv
from urllib.parse import urlencode
from pyquery import PyQuery as pq
import re
import json

# 设置请求头
headers = {
    'Host': 'm.weibo.cn',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Mobile Safari/537.36'
}


def time_formater(input_time_str):
    """
    将微博返回的时间字符串转换为指定格式的时间字符串
    """
    input_format = '%a %b %d %H:%M:%S %z %Y'
    output_format = '%Y-%m-%d %H:%M:%S'
    return datetime.strptime(input_time_str, input_format).strftime(output_format)


def get_single_page(page, keyword):
    """
    获取单页数据
    """
    base_url = 'https://m.weibo.cn/api/container/getIndex?'
    params = {
        'containerid': f'100103type=1&q=#{keyword}#',
        'page_type': 'searchall',
        'page': page
    }
    url = base_url + urlencode(params)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # 抛出异常，如果请求不成功
        json_data = response.json()
        return json_data
    except Exception as e:
        print(f"Error occurred while fetching page {page}: {e}")
        return None


def get_long_text(lid):
    """
    获取长文本内容
    """
    headers_longtext = {
        'Host': 'm.weibo.cn',
        'User-Agent': headers['User-Agent']
    }
    params = {
        'id': lid
    }
    url = 'https://m.weibo.cn/statuses/extend?' + urlencode(params)
    try:
        response = requests.get(url, headers=headers_longtext)
        response.raise_for_status()
        jsondata = response.json()
        tmp = jsondata.get('data')
        return pq(tmp.get("longTextContent")).text() if tmp else None
    except Exception as e:
        print(f"Error occurred while fetching long text for {lid}: {e}")
        return None


def parse_page(json_data):
    """
    解析页面返回的json数据
    """
    items = json_data.get('data', {}).get('cards', [])
    for item in items:
        if item.get('card_type') in [7, 8] or (item.get('card_type') == 11 and not item.get('card_group')):
            continue
        if 'mblog' in item:
            item = item['mblog']
        elif 'card_group' in item:
            item = item['card_group'][0]['mblog']
        if item:
            if item.get('isLongText') is False:
                text = pq(item.get("text")).text()
            else:
                text = get_long_text(item.get('id'))
            text = re.sub(r'#.*?#', '', text)  # 去除话题
            text = re.sub(r'【.*?】', '', text)  # 去除【】之间的内容
            text = re.sub(r'「.*?」', '', text)  # 去除「」之间的内容
            text = re.sub(r'[\U00010000-\U0010ffff]', '', text)  # 去除emoji等特殊符号
            text = re.sub(r"(回复)?(//)?\s*@\S*?\s*(:| |$)", " ", text)  # 去除正文中的@和回复/转发中的用户名
            text = re.sub(r"[\S+]", "", text)  # 去除表情符号
            url_re = re.compile(
                r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s('
                r')<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))',
                re.IGNORECASE)
            text = re.sub(url_re, "", text)  # 去除网址
            text = text.replace("转发微博", "")  # 去除无意义的词语
            text = re.sub(r"\s+", " ", text)  # 合并正文中过多的空格
            data = {
                'pid': item.get('id'),
                'user_name': item.get('user', {}).get('screen_name'),
                'uid': item.get('user', {}).get('id'),
                'gender': item.get('user', {}).get('gender'),
                'publish_time': time_formater(item.get('created_at')),
                'text': text,
                'like_count': item.get('attitudes_count', 0),
                'comment_count': item.get('comments_count', 0),
                'forward_count': item.get('reposts_count', 0)
            }
            yield data


def save_to_csv(data, file_path):
    """
    将数据保存到CSV文件
    """
    if not os.path.exists(file_path):
        with open(file_path, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['pid', '用户名', 'uid', '性别', '发布时间', '文本', '点赞', '评论数', '转发'])
    with open(file_path, mode='a+', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        for d in data:
            writer.writerow([
                d['pid'], d['user_name'], d['uid'], d['gender'],
                d['publish_time'], d['text'], d['like_count'],
                d['comment_count'], d['forward_count']
            ])


if __name__ == '__main__':
    keyword = '拒绝休息羞耻'
    result_file = f'{keyword}.csv'

    temp_data = []
    empty_times = 0

    for page in range(1, 50000):
        print(f'Page: {page}')
        json_data = get_single_page(page, keyword)
        if json_data is None:
            break
        if not json_data.get('ok'):
            empty_times += 1
        else:
            empty_times = 0
        if empty_times > 10:
            print('Consist empty over 10 times. Exiting...')
            break
        for result in parse_page(json_data):
            if result['text']:
                temp_data.append(result)
            else:
                print(f'空文本')
        save_to_csv(temp_data, result_file)
        print(f'Saved {len(temp_data)} rows to CSV.')
        temp_data = []
        time.sleep(random.randint(2, 4))
    print(f'Finished.')
