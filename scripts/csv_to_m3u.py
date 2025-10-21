import os
import csv

# CSV 文件
csv_file = "input/mysource/sum.csv"
# 图标文件夹
icon_dir = "png"
default_icon = "png/default.png"
# 输出目录
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# 分组优先顺序
group_order = ["央视频道", "卫视频道", "4K频道", "山东频道", "国际频道"]

# 两个地址源优先顺序
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

# 查找图标
for ch in channels:
    icon_path = os.path.join(icon_dir, f"{ch['name']}.png")
    if os.path.exists(icon_path):
        ch["icon"] = f"https://raw.githubusercontent.com/niuinyang/iptv-sum/main/{icon_path}"
    elif os.path.exists(default_icon):
        ch["icon"] = f"https://raw.githubusercontent.com/niuinyang/iptv-sum/main/{default_icon}"
    else:
        ch["icon"] = ""

# 分组排序函数
def group_sort_key(ch):
    if ch["group"] in group_order:
        return group_order.index(ch["group"])
    else:
        return len(group_order)  # 其他未列出的分组排在最后

# 地址源排序函数
def source_sort_key(ch, order):
    try:
        return order.index(ch["source"])
    except ValueError:
        return len(order)  # 未列出的放后面

# 生成 M3U 文件
def generate_m3u(filename, source_priority, remove_source=None):
    filtered = channels.copy()
    if remove_source:
        filtered = [ch for ch in filtered if ch["source"] != remove_source]
    # 先分组排序，再按地址源排序，再按频道名排序
    filtered.sort(key=lambda ch: (group_sort_key(ch), source_sort_key(ch, source_priority), ch["name"]))
    
    m3u_path = os.path.join(output_dir, filename)
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in filtered:
            extinf = f'#EXTINF:-1 tvg-id="" tvg-name="{ch["name"]}" tvg-logo="{ch["icon"]}" group-title="{ch["group"]}",{ch["name"]}'
            if ch["source"]:
                extinf = f"# {ch['source']}\n" + extinf
            f.write(f"{extinf}\n{ch['url']}\n")
    print(f"✅ 已生成 {filename}, 共 {len(filtered)} 条频道")

# 生成 dxl.m3u
generate_m3u("dxl.m3u", dxl_order, remove_source="济南移动")
# 生成 sjmz.m3u
generate_m3u("sjmz.m3u", sjmz_order)