import csv
import re
import unicodedata
from opencc import OpenCC
import os

# 文件路径
m3u_file = "output/working.m3u"
find_file = "input/network/find_international.csv"
output_dir = "input/network"
output_file = os.path.join(output_dir, "international_sum.csv")

# 确保目录存在
os.makedirs(output_dir, exist_ok=True)

# 简繁转换器（繁体 -> 简体）
cc = OpenCC('t2s')

# 标准化文本：繁转简 + 去掉空格和标点 + 小写
def normalize_text(text):
    if not text:
        return ""
    text = cc.convert(text)
    text = unicodedata.normalize("NFKC", text)
    text = ''.join(
        c for c in text
        if not (c.isspace() or unicodedata.category(c).startswith(('P', 'S')))
    )
    return text.lower()

# 读取要查找的国际电视台列表（第一列），保持顺序
with open(find_file, "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    search_names = [row[0].strip() for row in reader if row]

# 标准化搜索名
search_norm = [normalize_text(name) for name in search_names]

# 准备存储匹配结果
matches_dict = {name: [] for name in search_names}  # 按 find.csv 顺序存储结果
seen_urls = set()  # 去重 URL

# 读取 M3U 内容并匹配
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
                # 第一列 find.csv 名称，第二列地区，第三列 URL，第四列来源（固定“国际源”），第五列原始 tvg-name
                matches_dict[search_names[idx]].append([
                    search_names[idx],
                    "国际",
                    url_line,
                    "国际源",
                    tvg_name_original
                ])
                seen_urls.add(url_line)
                break
        i += 2
    else:
        i += 1

# 按 find.csv 顺序写入 CSV
with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["tvg-name", "地区", "URL", "来源", "原始tvg-name"])
    for name in search_names:
        writer.writerows(matches_dict[name])

print(f"匹配完成，共找到 {sum(len(v) for v in matches_dict.values())} 个频道，已输出到 {output_file}")
