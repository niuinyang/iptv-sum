import os
import re
from pypinyin import lazy_pinyin

input_dir = "input/mysource"
output_dir = "output"
csv_file = os.path.join(output_dir, "total.csv")
m3u_file = os.path.join(output_dir, "total.m3u")

os.makedirs(output_dir, exist_ok=True)

# 正则匹配 tvg-name 可选，group-title 可选
pattern = re.compile(
    r'#EXTINF:-1.*?(?:tvg-name="([^"]*)")?.*?(?:group-title="([^"]*)")?.*?,(.*?)\n(.*?)$',
    re.MULTILINE
)

rows = []

if not os.path.exists(input_dir):
    print(f"⚠️ 输入目录 {input_dir} 不存在，已自动创建，请上传 .m3u 文件后重新运行")
    os.makedirs(input_dir, exist_ok=True)
    exit(0)

# ---------- 1️⃣ 读取 M3U 文件 ----------
for file in os.listdir(input_dir):
    if not file.endswith(".m3u"):
        continue
    path = os.path.join(input_dir, file)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    matches = pattern.findall(text)
    for tvg_name, group, display_name, url in matches:
        # 保留原始频道名和显示名，不做统一化
        name = tvg_name.strip() or display_name.strip() or "未知频道"
        # 保留原始分组，如果为空才设“待分类”
        group_name = group.strip() if group and group.strip() else "待分类"
        rows.append((name, group_name, url.strip()))

# ---------- 2️⃣ 去重 + 拼音排序 ----------
def sort_key(item):
    return "".join(lazy_pinyin(item[0])).lower()

rows = sorted(set(rows), key=sort_key)

# ---------- 3️⃣ 输出 CSV ----------
with open(csv_file, "w", encoding="utf-8") as f:
    for name, group, url in rows:
        f.write(f"{name},{group},{url}\n")

# ---------- 4️⃣ 输出 M3U ----------
with open(m3u_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for name, group, url in rows:
        f.write(f'#EXTINF:-1 tvg-name="{name}" group-title="{group}",{name}\n{url}\n')

print(f"✅ 已输出 {len(rows)} 条记录")
print(f"  📄 CSV: {csv_file}")
print(f"  📺 M3U: {m3u_file}")