import os
import re
import csv

# 输入、输出目录
input_dir = "input/mysource"
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

csv_file = os.path.join(output_dir, "total.csv")

# 正则匹配 tvg-name 可选，group-title 可选
pattern = re.compile(
    r'#EXTINF:-1.*?tvg-name="([^"]*)".*?(?:group-title="([^"]*)")?.*?,.*?\n(.*)',
    re.MULTILINE
)

rows = []

if not os.path.exists(input_dir):
    print(f"⚠️ 输入目录 {input_dir} 不存在，请先上传 M3U 文件")
    exit(0)

# 遍历所有 M3U 文件
for file in os.listdir(input_dir):
    if not file.endswith(".m3u"):
        continue
    path = os.path.join(input_dir, file)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    matches = pattern.findall(text)
    for tvg_name, group, url in matches:
        tvg_name = tvg_name.strip() if tvg_name.strip() else "未知频道"
        group = group.strip() if group and group.strip() else "未分类"
        url = url.strip()
        rows.append([tvg_name, group, url])

# 去重
rows_unique = [list(x) for x in set(tuple(row) for row in rows)]

# 输出 CSV
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["频道名", "分组", "播放地址"])
    writer.writerows(rows_unique)

print(f"✅ 已生成 CSV 文件: {csv_file}, 共 {len(rows_unique)} 条记录")