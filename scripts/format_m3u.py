import os
import re
from pypinyin import lazy_pinyin

# 输入与输出路径
input_dir = "input/mysource"
output_dir = "output"
csv_file = os.path.join(output_dir, "total.csv")
m3u_file = os.path.join(output_dir, "total.m3u")

os.makedirs(output_dir, exist_ok=True)

# 正则匹配：tvg-name 可选，group-title 可选
pattern = re.compile(
    r'#EXTINF:-1.*?(?:tvg-name="([^"]*)")?.*?(?:group-title="([^"]*)")?.*?,(.*?)\n(.*?)$',
    re.MULTILINE
)

rows = []

# 检查输入目录
if not os.path.exists(input_dir):
    print(f"⚠️ 输入目录 {input_dir} 不存在，已自动创建（请上传 .m3u 文件后重新运行）")
    os.makedirs(input_dir, exist_ok=True)
    exit(0)

# 遍历输入目录下所有 .m3u 文件
for file in os.listdir(input_dir):
    if not file.endswith(".m3u"):
        continue

    file_path = os.path.join(input_dir, file)
    with open(file_path, encoding="utf-8") as f:
        text = f.read()

    matches = pattern.findall(text)
    for tvg_name, group, display_name, url in matches:
        tvg_name = tvg_name.strip() or display_name.strip() or "未知频道"
        group = group.strip() if group.strip() else "待分类"
        rows.append((tvg_name, group, url.strip()))

# 去重并按频道名拼音排序
def sort_key(item):
    tvg_name = item[0]
    return "".join(lazy_pinyin(tvg_name)).lower()

rows = sorted(set(rows), key=sort_key)

# 输出 CSV 文件
with open(csv_file, "w", encoding="utf-8") as f:
    for tvg_name, group, url in rows:
        f.write(f"{tvg_name},{group},{url}\n")

# 输出 M3U 文件
with open(m3u_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for tvg_name, group, url in rows:
        f.write(f'#EXTINF:-1 tvg-name="{tvg_name}" group-title="{group}",{tvg_name}\n{url}\n')

print(f"✅ 已输出 {len(rows)} 条记录：")
print(f"  📄 CSV: {csv_file}")
print(f"  📺 M3U: {m3u_file}")
