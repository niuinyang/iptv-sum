import os
import csv
import re
from collections import defaultdict

# ==============================
# 文件夹和图标配置
# ==============================
icon_dir = "png"
default_icon = os.path.join(icon_dir, "default.png")
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

fixed_csv = ["input/mysource/my_sum.csv"]
fixed_folder = "input/network/manual"
extra_folder = "output/sum_cvs"

# ==============================
# 分组优先级
# ==============================
group_order = [
    "央视频道", "卫视频道", "台湾频道", "香港频道",
    "澳门频道", "国际频道", "地方频道", "数字频道"
]

# ==============================
# 源优先级
# ==============================
dxl_priority = ["电信组播", "济南联通", "上海移动", "电信单播", "青岛联通"]
sjmz_priority = ["济南移动", "上海移动", "济南联通", "电信组播", "青岛联通", "电信单播"]

# ==============================
# 分组映射
# ==============================
GROUP_MAP = {
    "台湾": "台湾频道",
    "香港": "香港频道",
    "澳门": "澳门频道",
    "国际": "国际频道",
    "tw": "台湾频道",
    "hk": "香港频道",
    "mo": "澳门频道",
    "intl": "国际频道"
}

# ==============================
# 读取 CSV
# ==============================
def read_csv_files(paths, manual_group_map=None):
    channels = []
    for path in paths:
        if not os.path.exists(path):
            print(f"⚠️ 路径不存在: {path}")
            continue
        if os.path.isdir(path):
            for file in os.listdir(path):
                if file.endswith(".csv"):
                    channels += read_csv_files([os.path.join(path, file)], manual_group_map)
        else:
            with open(path, encoding="utf-8") as f:
                sample = f.read(1024)
                f.seek(0)
                delimiter = "\t" if "\t" in sample else ","
                reader = csv.reader(f, delimiter=delimiter)
                count = 0
                filename = os.path.basename(path).lower()
                for row in reader:
                    if len(row) >= 4:
                        name, group, url, source = row[:4]
                    elif len(row) == 2 and manual_group_map:
                        name, url = row
                        group = manual_group_map.get(filename, "未分类")
                        source = "手动"
                    else:
                        continue
                    # 映射分组名称
                    group = GROUP_MAP.get(group.strip(), group.strip())
                    channels.append({
                        "name": name.strip(),
                        "group": group,
                        "url": url.strip(),
                        "source": source.strip()
                    })
                    count += 1
                print(f"📄 读取 {path} 共 {count} 条数据")
    return channels

# ==============================
# 排序规则
# ==============================
def natural_key(name):
    m = re.match(r"CCTV(\d+)", name.upper())
    if m:
        return (0, int(m.group(1)))
    return (1, name.lower())

def group_key(group):
    if group in group_order:
        return group_order.index(group)
    return len(group_order)

def source_priority(source, order):
    try:
        return order.index(source)
    except ValueError:
        return len(order)

# ==============================
# M3U 生成函数
# ==============================
def write_m3u(channels_dict, output_file, source_order=None, exclude_sources=None):
    total = 0
    exclude_sources = exclude_sources or []
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for group, name_dict in sorted(channels_dict.items(), key=lambda x: group_key(x[0])):
            for name, sources in sorted(name_dict.items(), key=lambda x: natural_key(x[0])):
                filtered_sources = [s for s in sources if s["source"] not in exclude_sources]
                if source_order:
                    filtered_sources.sort(key=lambda s: source_priority(s["source"], source_order))
                for s in filtered_sources:
                    logo_path = os.path.join(icon_dir, f"{name}.png")
                    logo = logo_path if os.path.exists(logo_path) else default_icon
                    extinf = f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{s["group"]}",{name}'
                    f.write(f"{extinf}\n{s['url']}\n")
                    total += 1
    print(f"✅ 已生成 {output_file}，共 {total} 条频道")

# ==============================
# 主程序
# ==============================
def main():
    # 手动 CSV 分组映射
    manual_group_map = {
        "network_hk_manual.csv": "香港频道",
        "network_mo_manual.csv": "澳门频道",
        "network_tw_manual.csv": "台湾频道",
        "netwotk_intl_manual.csv": "国际频道"
    }

    # 固定源
    fixed_channels = read_csv_files(fixed_csv + [fixed_folder], manual_group_map)

    # 建立固定源频道名集合（正则匹配用）
    fixed_names = [re.escape(ch["name"]) for ch in fixed_channels]
    fixed_pattern = re.compile("|".join(fixed_names), re.I)

    # 补充源
    extra_channels = read_csv_files([extra_folder])

    # 补充源只保留固定源已有的频道
    extra_filtered = [ch for ch in extra_channels if fixed_pattern.search(ch["name"])]

    # 合并频道
    combined = defaultdict(lambda: defaultdict(list))
    for ch in fixed_channels:
        combined[ch["group"]][ch["name"]].append(ch)
    for ch in extra_filtered:
        combined[ch["group"]][ch["name"]].append(ch)

    # 生成 M3U 文件
    write_m3u(combined, os.path.join(output_dir, "total.m3u"))
    write_m3u(combined, os.path.join(output_dir, "dxl.m3u"), source_order=dxl_priority, exclude_sources=["济南移动"])
    write_m3u(combined, os.path.join(output_dir, "sjmz.m3u"), source_order=sjmz_priority)

    print("✅ 所有 M3U 文件生成完成！")

if __name__ == "__main__":
    main()