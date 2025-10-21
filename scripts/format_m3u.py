import os
import re

# 输入与输出路径
input_dir = "input/yuan"
output_dir = "output"
output_file = os.path.join(output_dir, "total.csv")

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 匹配 M3U 格式的正则
pattern = re.compile(
    r'#EXTINF:-1.*?tvg-name="([^"]+)".*?group-title="([^"]+)".*?,(.*?)\n(.*?)$',
    re.MULTILINE
)

rows = []

# 遍历 input/yuan 文件夹下所有 .m3u 文件
for file in os.listdir(input_dir):
    if not file.endswith(".m3u"):
        continue

    file_path = os.path.join(input_dir, file)
    with open(file_path, encoding="utf-8") as f:
        text = f.read()

    matches = pattern.findall(text)
    for tvg_name, group, display_name, url in matches:
        rows.append(f"{tvg_name},{group},{url}")

# 去重（可选）
rows = sorted(set(rows))

# 写入输出文件
with open(output_file, "w", encoding="utf-8") as out:
    out.write("\n".join(rows))

print(f"✅ 已输出 {len(rows)} 条记录到 {output_file}")
