import os
import re
from collections import Counter
from pypinyin import lazy_pinyin

input_dir = "input/mysource"
output_dir = "output"
csv_file = os.path.join(output_dir, "total.csv")
m3u_file = os.path.join(output_dir, "total.m3u")
mapping_file = os.path.join(output_dir, "auto_mapping.csv")

os.makedirs(output_dir, exist_ok=True)

# 正则匹配 tvg-name 可选，group-title 可选
pattern = re.compile(
    r'#EXTINF:-1.*?(?:tvg-name="([^"]*)")?.*?(?:group-title="([^"]*)")?.*?,(.*?)\n(.*?)$',
    re.MULTILINE
)

# ---------- 1️⃣ 收集原始频道名生成映射表 ----------
all_names = []

if not os.path.exists(input_dir):
    print(f"⚠️ 输入目录 {input_dir} 不存在，已自动创建，请上传 .m3u 文件后重新运行")
    os.makedirs(input_dir, exist_ok=True)
    exit(0)

for file in os.listdir(input_dir):
    if not file.endswith(".m3u"):
        continue
    path = os.path.join(input_dir, file)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    matches = pattern.findall(text)
    for tvg_name, group, display_name, url in matches:
        name = tvg_name.strip() or display_name.strip()
        if name:
            # 清理名字，但保留 4K
            name = name.replace('（', '(').replace('）', ')')
            name = re.sub(r'高清|1080P|720P', '', name, flags=re.IGNORECASE)
            name = name.strip()
            all_names.append(name)

# 生成映射表（默认原样映射，可手动调整 auto_mapping.csv）
counter = Counter(all_names)
mapping = {name: name for name in all_names}

with open(mapping_file, "w", encoding="utf-8") as f:
    for original, standard in mapping.items():
        f.write(f"{original},{standard}\n")

print(f"✅ 自动生成映射表完成，保存在 {mapping_file}")

# ---------- 2️⃣ 使用映射表统一化处理 ----------
mapping_dict = {}
with open(mapping_file, encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split(",")
        if len(parts) == 2:
            mapping_dict[parts[0]] = parts[1]

def normalize_name(name):
    name = name.strip()
    name = name.replace('（', '(').replace('）', ')')
    name = re.sub(r'高清|1080P|720P', '', name, flags=re.IGNORECASE)
    name = name.strip()
    return mapping_dict.get(name, name)

# ---------- 3️⃣ 处理 M3U 文件 ----------
rows = []

for file in os.listdir(input_dir):
    if not file.endswith(".m3u"):
        continue
    path = os.path.join(input_dir, file)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    matches = pattern.findall(text)
    for tvg_name, group, display_name, url in matches:
        tvg_name = tvg_name.strip() or display_name.strip() or "未知频道"
        tvg_name = normalize_name(tvg_name)
        group = group.strip() if group and group.strip() else "待分类"
        rows.append((tvg_name, group, url.strip()))

# ---------- 4️⃣ 去重 + 拼音排序 ----------
def sort_key(item):
    tvg_name = item[0]
    return "".join(lazy_pinyin(tvg_name)).lower()

rows = sorted(set(rows), key=sort_key)

# ---------- 5️⃣ 输出 CSV ----------
with open(csv_file, "w", encoding="utf-8") as f:
    for tvg_name, group, url in rows:
        f.write(f"{tvg_name},{group},{url}\n")

# ---------- 6️⃣ 输出 M3U ----------
with open(m3u_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for tvg_name, group, url in rows:
        f.write(f'#EXTINF:-1 tvg-name="{tvg_name}" group-title="{group}",{tvg_name}\n{url}\n')

print(f"✅ 已输出 {len(rows)} 条记录")
print(f"  📄 CSV: {csv_file}")
print(f"  📺 M3U: {m3u_file}")
