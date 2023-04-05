import re
import math


def splitter(article_path, k=3):
    with open(article_path) as f:
        lines = f.readlines()
        total_lines = len(lines)
        lines_per_file = math.ceil(total_lines / k)
        for i in range(k):
            start = i * lines_per_file
            end = min((i + 1) * lines_per_file, total_lines)
            yield lines[start:end]


def mapper(lines):
    word_count = {}
    for line in lines:
        words = re.findall(r'\w+', line.lower())
        for word in words:
            if word not in word_count:
                word_count[word] = 1
            else:
                word_count[word] += 1
    return word_count


def reducer(word_counts):
    word_count = {}
    for wc in word_counts:
        for word, count in wc.items():
            if word not in word_count:
                word_count[word] = count
            else:
                word_count[word] += count
    return word_count


word_counts = []
for lines in splitter('datasets/TheAdventuresOfTomSawyer_MarkTwain/TheAdventuresOfTomSawyer_MarkTwain_Catalan.txt', k=3):
    word_counts.append(mapper(lines))

word_count = reducer(word_counts)
for word, count in word_count.items():
    print(f"{word}: {count}")
