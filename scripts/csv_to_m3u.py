import os
import csv

# 输入 CSV 文件路径
csv_file = "input/mysource/sum.csv"
# PNG 图标文件夹
icon_dir = "png"
# 输出 M3U 文件
output_dir = "output"
m3u_file = os.path.join(output_dir, "total.m3u")

os.makedirs(output_dir, exist_ok=True)

# 打开 CSV 并生成 M3U
with open(csv_file, newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)  # 跳过表头
    lines = []

    for row in reader:
        if len(row) < 3:
            continue
        name = row[0].strip()
        group = row[1].strip() if row[1].strip() else "未分类"
        url = row[2].strip()
        source = row[3].strip() if len(row) > 3 else ""
        
        # 查找图标
        icon_path = os.path.join(icon_dir, f"{name}.png")
        if os.path.exists(icon_path):
            icon_url = f"https://raw.githubusercontent.com/niuinyang/iptv-sum/main/{icon_path}"
        else:
            icon_url = ""

        # 生成 EXTINF 行
        extinf = f'#EXTINF:-1 tvg-id="" tvg-name="{name}" tvg-logo="{icon_url}" group-title="{group}",{name}'
        lines.append(f"{extinf}\n{url}")

# 写入 M3U 文件
with open(m3u_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    f.write("\n".join(lines))

print(f"✅ 已生成 M3U 文件: {m3u_file}, 共 {len(lines)} 条频道")