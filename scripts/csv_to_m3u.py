import os
import csv
import re
from collections import defaultdict

# CSV 文件路径
csv_files = [
    "input/mysource/my_sum.csv",
    "input/network/taiwan_sum.csv"
]

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

# 地址源排序
dxl_order = ["电信组播", "济南联通", "上海移动", "电信单播", "青岛联通"]
sjmz_order = ["济南移动", "上海移动", "济南联通", "电信组播", "青岛联通", "电信单播"]

# 读取 CSV
channels = []
for csv_file in csv_files:
    with open(csv_file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < 3:
                continue
            name = row[0].strip()
            group = row[1].strip() if row[1].strip() else "未分类"
            if "taiwan" in csv_file.lower():
                group = "台湾频道"
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

# 分组排序规则
# 优先级从 0 开始，数字越小越靠前
priority_groups = [
    "央视频道",
    "4K频道",
    "卫视频道",
    "国际频道",
    "台湾频道"
]

# 其他分组按拼音排序，但排除数字频道和电台广播
other_groups = sorted(set(ch["group"] for ch in channels if ch["group"] not in priority_groups + ["数字频道", "电台广播"]))
# 构建 group_priority
group_priority = {name: i + len(priority_groups) for i, name in enumerate(other_groups)}
# 数字频道倒数第二
group_priority["数字频道"] = len(priority_groups) + len(other_groups)
# 电台广播最后
group_priority["电台广播"] = len(priority_groups) + len(other_groups) + 1
# 已有的固定顺序
for i, g in enumerate(priority_groups):
    group_priority[g] = i

# 分组排序 key
def group_sort_key(ch):
    return (group_priority.get(ch["group"], 999), natural_key(ch["name"]))

# 地址源排序
def source_sort_key(ch, order):
    try:
        return order.index(ch["source"])
    except ValueError:
        return len(order)

# 生成 M3U 文件
def generate_m3u(filename, source_priority, remove_source=None):
    filtered = [ch for ch in channels if ch["source"] != remove_source] if remove_source else channels.copy()

    # 分组排序 + 频道名自然排序
    filtered.sort(key=group_sort_key)

    # 分组内部按 source 排序
    grouped = defaultdict(list)
    for ch in filtered:
        grouped[ch["group"]].append(ch)

    final_list = []
    for group_name in sorted(grouped.keys(), key=lambda g: group_priority.get(g, 999)):
        group_items = grouped[group_name]
        # 组内按频道名自然排序
        group_items.sort(key=lambda ch: natural_key(ch["name"]))
        # 同名频道按 source_priority 排序
        name_dict = defaultdict(list)
        for ch in group_items:
            name_dict[ch["name"]].append(ch)
        for name in sorted(name_dict.keys(), key=natural_key):
            items = name_dict[name]
            items.sort(key=lambda ch: source_sort_key(ch, source_priority))
            final_list.extend(items)

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
