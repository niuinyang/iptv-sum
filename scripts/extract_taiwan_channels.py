import csv
import re
import unicodedata
from opencc import OpenCC

# 文件路径
m3u_file = "output/working.m3u"
find_file = "input/network/find.csv"
output_file = "input/network/sum.csv"

# 简繁转换器
cc = OpenCC('t2s')  # 繁体 -> 简体

# 标准化文本：繁转简 + 去掉空格和标点
def normalize_text(text):
    if not text:
        return ""
    text = cc.convert(text)  # 繁体 -> 简体
    text = unicodedata.normalize("NFKC", text)  # 标准化字符
    # 移除空格和标点符号
    text = ''.join(
        c for c in text
        if not (c.isspace() or unicodedata.category(c).startswith(('P', 'S')))
    )
    return text.lower()

# 读取要查找的电视台列表（第一列），保持顺序
with open(find_file, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    search_names = [row[0].strip() for row in reader if row]

# 标准化搜索名
search_norm = [normalize_text(name) for name in search_names]

# 读取 M3U 内容并匹配
matches_dict = {name: [] for name in search_names}  # 按 find.csv 顺序存储结果
seen_urls = set()  # 去重 URL

with open(m3u_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

i = 0
while i < len(lines):
    line = lines[i].strip()
    if line.startswith("#EXTINF:"):
        info_line = line
        url_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if url_line in seen_urls:
            i += 2
            continue
        # 提取 tvg-name
        match_name = re.search(r'tvg-name="([^"]+)"', info_line)
        tvg_name_original = match_name.group(1) if match_name else ""
        tvg_norm = normalize_text(tvg_name_original)

        # 遍历搜索列表，看是否匹配
        for idx, name_norm in enumerate(search_norm):
            if name_norm in tvg_norm:
                matches_dict[search_names[idx]].append([tvg_name_original, "台湾", url_line])
                seen_urls.add(url_line)
                break
        i += 2
    else:
        i += 1

# 按 find.csv 顺序写入 CSV
with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["tvg-name", "地区", "URL"])
    for name in search_names:
        writer.writerows(matches_dict[name])

print(f"匹配完成，共找到 {sum(len(v) for v in matches_dict.values())} 个频道，已输出到 {output_file}")
