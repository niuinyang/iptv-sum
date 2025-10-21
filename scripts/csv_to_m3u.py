import os
import csv
import re
from itertools import groupby

# CSV 文件路径
csv_file = "input/mysource/sum.csv"
# 图标文件夹
icon_dir = "png"
default_icon = "png/default.png"
# 输出目录
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# CCTV 频道自然排序
def natural_key(name):
    m = re.match(r"(CCTV-?)(\d+)", name, re.I)
    if m:
        prefix, num = m.groups()
        return (prefix.lower(), int(num))
    else:
        return (name.lower(), 0)

cctv_order = ["CCTV-1", "CCTV-2", "CCTV-3", "CCTV-4", "CCTV-5", "CCTV-6", "CCTV-7", "CCTV-8", "CCTV-9", "CCTV-10"]

# 地址源排序
dxl_order = ["电信组播", "济南联通", "上海移动", "电信单播", "青岛联通"]
sjmz_order = ["济南移动", "上海移动", "济南联通", "电信组播", "青岛联通", "电信单播"]

# 读取 CSV
channels = []
with open(csv_file, newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader)  # 跳过表头
    for row in reader:
        if len(row) < 3:
            continue
        name = row[0].strip()
        group = row[1].strip() if row[1].strip() else "未分类"
        url = row[2].strip()
        source = row[3].strip() if len(row) > 3 else ""
        channels.append({
            "name": name,
            "group": group,
            "url": url,
            "source": source
        })

# 图标处理
for ch in channels:
    icon_path = os.path.join(icon_dir, f"{ch['name']}.png")
    if os.path.exists(icon_path):
        ch["icon"] = f"https://raw.githubusercontent.com/niuinyang/iptv-sum/main/{icon_path}"
    elif os.path.exists(default_icon):
        ch["icon"] = f"https://raw.githubusercontent.com/niuinyang/iptv-sum/main/{default_icon}"
    else:
        ch["icon"] = ""

# 分组排序：央视频道按 CCTV 自然顺序，其他按拼音
other_groups = sorted(set(ch["group"] for ch in channels if ch["group"] != "央视频道"))
group_priority = {name: i+len(cctv_order) for i, name in enumerate(other_groups)}

def group_sort_key(ch):
    if ch["group"] == "央视频道":
        try:
            return cctv_order.index(ch["name"])
        except ValueError:
            return len(cctv_order)
    else:
        return group_priority.get(ch["group"], len(cctv_order) + len(group_priority))

# 地址源排序
def source_sort_key(ch, order):
    try:
        return order.index(ch["source"])
    except ValueError:
        return len(order)

# 生成 M3U 文件
def generate_m3u(filename, source_priority, remove_source=None):
    filtered = channels.copy()
    if remove_source:
        filtered = [ch for ch in filtered if ch["source"] != remove_source]

    # 先按分组和频道名自然排序
    filtered.sort(key=lambda ch: (group_sort_key(ch), natural_key(ch["name"])))

    # 每个频道内部按 source_priority 排序
    final_list = []
    for name, group_items in groupby(filtered, key=lambda ch: ch["name"]):
        group_items = list(group_items)
        group_items.sort(key=lambda ch: source_sort_key(ch, source_priority))
        final_list.extend(group_items)

    # 写入 M3U
    m3u_path = os.path.join(output_dir, filename)
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in final_list:
            extinf = f'#EXTINF:-1 tvg-id="" tvg-name="{ch["name"]}" tvg-logo="{ch["icon"]}" group-title="{ch["group"]}",{ch["name"]}'
            if ch["source"]:
                extinf = f"# {ch['source']}\n" + extinf
            f.write(f"{extinf}\n{ch['url']}\n")

    print(f"✅ 已生成 {filename}, 共 {len(final_list)} 条频道")

# 生成 dxl.m3u（去掉济南移动）
generate_m3u("dxl.m3u", dxl_order, remove_source="济南移动")
# 生成 sjmz.m3u
generate_m3u("sjmz.m3u", sjmz_order)