import os
import csv

# 输入输出路径
input_dir = "output/sum_cvs"
output_dir = "output/sum_m3u"
os.makedirs(output_dir, exist_ok=True)

# 遍历文件夹下 CSV 文件
for csv_file in os.listdir(input_dir):
    if not csv_file.endswith(".csv"):
        continue

    csv_path = os.path.join(input_dir, csv_file)
    m3u_name = os.path.splitext(csv_file)[0] + ".m3u"
    m3u_path = os.path.join(output_dir, m3u_name)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        lines = ["#EXTM3U\n"]
        for row in reader:
            tvg_name = row.get("tvg-name", "").strip()
            region = row.get("地区", "").strip()
            url = row.get("URL", "").strip()
            if not url:
                continue
            group_title = region if region else "其他"
            extinf = f'#EXTINF:-1 tvg-name="{tvg_name}" group-title="{group_title}",{tvg_name}'
            lines.append(extinf)
            lines.append(url)

    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ 已生成 {m3u_path}")
