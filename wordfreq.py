import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import jieba
from collections import Counter
import os

# 读取所有CSV文件并合并'text'列
csv_files = [file for file in os.listdir() if file.endswith('.csv')]

all_text = ''
for file in csv_files:
    df = pd.read_csv(file)
    if '文本' in df.columns:
        all_text += ' '.join(df['文本'])

with open('all_text.txt', 'w', encoding='utf-8') as f:
    f.write(all_text)
# 分词并去除停用词
stopwords = set()
with open('chinese_stopwords.txt', 'r', encoding='utf-8') as f:
    for line in f:
        stopwords.add(line.strip())

seg_list = jieba.cut(all_text)
filtered_words = [word for word in seg_list if word.strip() and word not in stopwords]

# 统计词频
word_freq = Counter(filtered_words)
sorted_word_freq = dict(sorted(word_freq.items(), key=lambda x: x[1], reverse=True))

# 保存词频到CSV文件
word_freq_df = pd.DataFrame(sorted_word_freq.items(), columns=['词语', '词频'])
word_freq_df.to_csv('word_frequency.csv', index=False, encoding='utf-8')

# 生成词云
wordcloud = WordCloud(font_path='simhei.ttf').generate_from_frequencies(sorted_word_freq)

# 显示词云
plt.figure(figsize=(10, 8))
plt.imshow(wordcloud, interpolation='bilinear')
plt.axis('off')
plt.show()