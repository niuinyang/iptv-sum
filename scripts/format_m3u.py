import os
import re
from pypinyin import lazy_pinyin

input_dir = "input/mysource"
output_dir = "output"
csv_file = os.path.join(output_dir, "total.csv")
m3u_file = os.path.join(output_dir, "total.m3u")

os.makedirs(output_dir, exist_ok=True)

pattern = re.compile(
    r'#EXTINF:-1.*?tvg-name="(?P<tvg_name>[^"]*)".*?(?:group-title="(?P<group>[^"]*)")?.*?,(?P<display_name>.*?)\n(?P<url>.*)',
    re.MULTILINE
)

rows = []

if not os.path.exists(input_dir):
    os.makedirs(input_dir, exist_ok=True)
    exit(0)

for file in os.listdir(input_dir):
    if not file.endswith(".m3u"):
        continue
    path = os.path.join(input_dir, file)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    matches = pattern.finditer(text)
    for m in matches:
        tvg_name = m.group("tvg_name").strip() if m.group("tvg_name") else m.group("display_name").strip()
        group = m.group("group").strip() if m.group("group") else "待分类"
        url = m.group("url").strip()
        rows.append((tvg_name, group, url))

# 去重 + 拼音排序
def sort_key(item):
    return "".join(lazy_pinyin(item[0])).lower()

rows = sorted(set(rows), key=sort_key)

# 输出 CSV
with open(csv_file, "w", encoding="utf-8") as f:
    for name, group, url in rows:
        f.write(f"{name},{group},{url}\n")

# 输出 M3U
with open(m3u_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for name, group, url in rows:
        f.write(f'#EXTINF:-1 tvg-name="{name}" group-title="{group}",{name}\n{url}\n')

print(f"✅ 输出 {len(rows)} 条记录")
print(f"  📄 CSV: {csv_file}")
print(f"  📺 M3U: {m3u_file}")