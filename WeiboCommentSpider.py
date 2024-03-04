import time
import random
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re

def fetchUrl(pid, uid, max_id):

    url = "https://weibo.com/ajax/statuses/buildComments"

    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    }

    params = {
        "flow" : 0,
        "is_reload" : 1,
        "id" : pid,
        "is_show_bulletin" : 2,
        "is_mix" : 0,
        "max_id" : max_id,
        "count" : 20,
        "uid" : uid,
    }

    r = requests.get(url, headers = headers, params = params)
    return r.json()

def parseJson(jsonObj):

    data = jsonObj["data"]
    max_id = jsonObj["max_id"]
    flag = 0
    commentData = []
    for item in data:
        # 评论id
        comment_Id = item["id"]
        # 评论内容
        text = BeautifulSoup(item["text"], "html.parser").text
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'#.*?#', '', text)  # 去除话题
        text = re.sub(r'【.*?】', '', text)  # 去除【】之间的内容
        text = re.sub(r'「.*?」', '', text)  # 去除「」之间的内容
        text = re.sub(r'[\U00010000-\U0010ffff]', '', text)  # 去除emoji等特殊符号
        text = re.sub(r"(回复)?(//)?\s*@\S*?\s*(:| |$)", " ", text)  # 去除正文中的@和回复/转发中的用户名
        text = re.sub(r"\\[\S+\\]", "", text)  # 去除表情符号
        url_re = re.compile(
            r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s('
            r')<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))',
            re.IGNORECASE)
        text = re.sub(url_re, "", text)  # 去除网址
        text = text.replace("转发微博", "")  # 去除无意义的词语
        text = re.sub(r"\s+", " ", text)  # 合并正文中过多的空格
        if text == '':
            flag = 1;
        # 评论时间
        created_at = item["created_at"]
        # 点赞数
        like_counts = item["like_counts"]
        # 评论数
        total_number = item["total_number"]
        # 评论者 id，name，city
        user = item["user"]
        userID = user["id"]
        dataItem = [comment_Id, created_at, userID, like_counts, total_number, text]
        print(dataItem)
        commentData.append(dataItem)

    return commentData, max_id, flag

def save_data(data, path, filename):

    if not os.path.exists(path):
        os.makedirs(path)

    dataframe = pd.DataFrame(data)
    dataframe.to_csv(path + filename, encoding='utf_8_sig', mode='a', index=False, sep=',', header=False )

if __name__ == "__main__":
    # 读取包含pid和uid的CSV文件
    input_csv_file = "不要有休息羞耻.csv"
    output_csv_file = "不要有休息羞耻_评论.csv"

    # 读取CSV文件
    df = pd.read_csv(input_csv_file)

    # 初始化保存结果的CSV文件
    csvHeader = [["pid", "发布时间", "uid", "点赞数", "回复数", "文本"]]
    save_data(csvHeader, "./", output_csv_file)
    # 遍历每一行，提取pid和uid，并爬取评论数据
    for index, row in df.iterrows():
        pid = row['pid']
        uid = row['uid']
        max_id = 0
        consecutive_empty_responses = 0
        while True:
            # 获取评论数据
            html = fetchUrl(pid, uid, max_id)
            data = html["data"]

            # 检查响应是否为空
            if consecutive_empty_responses >= 30:  # 连续空响应次数超过30次时跳出循环
                print("连续空响应超过30次，退出循环")
                break
            if not data:
                consecutive_empty_responses += 1
                comments, max_id, flag = parseJson(html)
                save_data(comments, "./", output_csv_file)
                # 如果max_id为0，表示爬取结束
                if max_id == 0:
                    print("评论已爬取完毕，退出循环")
                    break
            else:
                consecutive_empty_responses = 0  # 重置连续空响应计数
                comments, max_id, flag = parseJson(html)
                if flag == 1:
                    print("评论为空，退出循环")
                    break;
                save_data(comments, "./", output_csv_file)
                # 如果max_id为0，表示爬取结束
                if max_id == 0:
                    print("评论已爬取完毕，退出循环")
                    break
            # 等待一段时间再进行下一次请求，避免请求过于频繁
            time.sleep(random.randint(2, 6))