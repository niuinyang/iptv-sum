import os
import re

# 输入与输出路径
input_dir = "input/mysource"
output_dir = "output"
csv_file = os.path.join(output_dir, "total.csv")
m3u_file = os.path.join(output_dir, "total.m3u")

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 匹配 M3U 格式的正则
pattern = re.compile(
    r'#EXTINF:-1.*?tvg-name="([^"]+)".*?group-title="([^"]+)".*?,(.*?)\n(.*?)$',
    re.MULTILINE
)

rows = []

# 遍历 input/mysource 下所有 .m3u 文件
for file in os.listdir(input_dir):
    if not file.endswith(".m3u"):
        continue

    file_path = os.path.join(input_dir, file)
    with open(file_path, encoding="utf-8") as f:
        text = f.read()

    matches = pattern.findall(text)
    for tvg_name, group, display_name, url in matches:
        rows.append((tvg_name.strip(), group.strip(), url.strip()))

# 去重并排序
rows = sorted(set(rows), key=lambda x: (x[1], x[0]))

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
