import os
import csv
import re
from collections import defaultdict

# ==============================
# 配置
# ==============================
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

icon_dir = "png"
default_icon = os.path.join(icon_dir, "default.png")

# 仅处理自有源 CSV
mysource_csv = os.path.join("input", "mysource", "my_sum.csv")
if not os.path.exists(mysource_csv):
    raise FileNotFoundError(f"❌ 未找到自有源 CSV: {mysource_csv}")

# ==============================
# CCTV 自然排序
# ==============================
def natural_key(name):
    """用于自然排序，如 CCTV-1, CCTV-10 排序正确"""
    m = re.match(r"(CCTV-?)(\d+)", name, re.I)
    if m:
        prefix, num = m.groups()
        return (prefix.lower(), int(num))
    else:
        return (name.lower(), 0)

# 源优先级
dxl_order = ["电信组播", "济南联通", "上海移动", "电信单播", "青岛联通"]
sjmz_order = ["济南移动", "上海移动", "济南联通", "电信组播", "青岛联通", "电信单播"]

# ==============================
# CSV 读取函数
# ==============================
def read_csv(file_path):
    results = []
    with open(file_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        for row in reader:
            if len(row) < 3:
                continue
            name = row[0].strip()
            group = row[1].strip() if len(row) > 1 and row[1].strip() else "未分类"
            url = row[2].strip()
            source = row[3].strip() if len(row) > 3 else ""
            results.append({
                "name": name,
                "group": group,
                "url": url,
                "source": source
            })
    return results

# ==============================
# 加载频道
# ==============================
channels = read_csv(mysource_csv)
print(f"✅ 已加载自有源频道 {len(channels)} 条")

# ==============================
# 去重
# ==============================
seen_urls = set()
final_channels = []
for ch in channels:
    if ch["url"] not in seen_urls:
        seen_urls.add(ch["url"])
        final_channels.append(ch)

print(f"✅ 去重后剩余 {len(final_channels)} 条")

# ==============================
# 图标处理
# ==============================
for ch in final_channels:
    icon_path = os.path.join(icon_dir, f"{ch['name']}.png")
    if os.path.exists(icon_path):
        ch["icon"] = f"https://raw.githubusercontent.com/niuinyang/iptv-sum/main/{icon_path}"
    elif os.path.exists(default_icon):
        ch["icon"] = f"https://raw.githubusercontent.com/niuinyang/iptv-sum/main/{default_icon}"
    else:
        ch["icon"] = ""

# ==============================
# 分组排序规则
# ==============================
priority_groups = ["央视频道", "4K频道", "卫视频道"]
other_groups = sorted(
    set(ch["group"] for ch in final_channels if ch["group"] not in priority_groups + ["数字频道", "电台广播"])
)
group_priority = {name: i + len(priority_groups) for i, name in enumerate(other_groups)}
group_priority["数字频道"] = len(priority_groups) + len(other_groups)
group_priority["电台广播"] = len(priority_groups) + len(other_groups) + 1
for i, g in enumerate(priority_groups):
    group_priority[g] = i

def group_sort_key(ch):
    return (group_priority.get(ch["group"], 999), natural_key(ch["name"]))

def source_sort_key(ch, order):
    try:
        return order.index(ch["source"])
    except ValueError:
        return len(order)

# ==============================
# M3U 生成函数
# ==============================
def generate_m3u(filename, source_priority):
    filtered = final_channels.copy()
    filtered.sort(key=group_sort_key)

    grouped = defaultdict(list)
    for ch in filtered:
        grouped[ch["group"]].append(ch)

    final_list = []
    for group_name in sorted(grouped.keys(), key=lambda g: group_priority.get(g, 999)):
        group_items = grouped[group_name]
        group_items.sort(key=lambda ch: natural_key(ch["name"]))
        name_dict = defaultdict(list)
        for ch in group_items:
            name_dict[ch["name"]].append(ch)
        for name in sorted(name_dict.keys(), key=natural_key):
            items = name_dict[name]
            items.sort(key=lambda ch: source_sort_key(ch, source_priority))
            final_list.extend(items)

    m3u_path = os.path.join(output_dir, filename)
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in final_list:
            extinf = f'#EXTINF:-1 tvg-id="" tvg-name="{ch["name"]}" tvg-logo="{ch["icon"]}" group-title="{ch["group"]}",{ch["name"]}'
            if ch["source"]:
                extinf = f"# {ch['source']}\n" + extinf
            f.write(f"{extinf}\n{ch["url"]}\n")

    print(f"✅ 已生成 {filename}, 共 {len(final_list)} 条频道")

# ==============================
# 输出文件
# ==============================
generate_m3u("dxl.m3u", dxl_order)
generate_m3u("sjmz.m3u", sjmz_order)
generate_m3u("total.m3u", dxl_order)
