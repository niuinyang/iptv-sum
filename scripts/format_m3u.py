import os
import re
import csv

input_dir = "input/mysource"
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

csv_file = os.path.join(output_dir, "total.csv")

# 用于提取 tvg-name 和 group-title
tvg_pattern = re.compile(r'tvg-name="([^"]*)"')
group_pattern = re.compile(r'group-title="([^"]*)"')

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
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("#EXTINF"):
            # 提取 tvg-name
            tvg_name_match = tvg_pattern.search(line)
            tvg_name = tvg_name_match.group(1).strip() if tvg_name_match else "未知频道"
            
            # 提取 group-title
            group_match = group_pattern.search(line)
            group = group_match.group(1).strip() if group_match else "未分类"
            
            # 下一行通常是 URL
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
            else:
                url = ""
            
            rows.append([tvg_name, group, url])

# 去重
rows_unique = [list(x) for x in set(tuple(row) for row in rows)]

# 输出 CSV
with open(csv_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["频道名", "分组", "播放地址"])
    writer.writerows(rows_unique)

print(f"✅ 已生成 CSV 文件: {csv_file}, 共 {len(rows_unique)} 条记录")