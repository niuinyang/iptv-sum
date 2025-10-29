import os
import csv
import re
from datetime import datetime

# ==============================
# 配置区
# ==============================
SOURCE_DIR = "input/network/network_sources"   # 已下载的 m3u 源目录
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MERGED_M3U = os.path.join(OUTPUT_DIR, "merge_total.m3u")
MERGED_CSV = os.path.join(OUTPUT_DIR, "merge_total.csv")

# ==============================
# 工具函数
# ==============================

def normalize_name(name: str) -> str:
    """去除特殊字符并标准化频道名"""
    name = re.sub(r"\s*\[.*?\]|\(.*?\)|（.*?）", "", name)  # 去括号
    name = re.sub(r"[\s_]+", "", name)  # 去空格和下划线
    return name.strip().lower()


def parse_m3u(file_path: str):
    """解析 M3U 文件为 (频道名, URL, LOGO, 分组)"""
    entries = []
    if not os.path.exists(file_path):
        return entries

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    name, logo, group, url = None, None, None, None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            name_match = re.search(r'tvg-name="([^"]+)"', line)
            logo_match = re.search(r'tvg-logo="([^"]+)"', line)
            group_match = re.search(r'group-title="([^"]+)"', line)
            name_inline = re.split(",", line)[-1].strip() if "," in line else None

            name = (name_match.group(1) if name_match else name_inline) or "未知频道"
            logo = logo_match.group(1) if logo_match else ""
            group = group_match.group(1) if group_match else ""
        elif line and not line.startswith("#"):
            url = line
            entries.append((name, url, logo, group))
            name, logo, group, url = None, None, None, None
    return entries


# ==============================
# 主逻辑
# ==============================

def merge_all_sources():
    all_entries = []
    seen = set()

    if not os.path.exists(SOURCE_DIR):
        print(f"❌ 未找到目录：{SOURCE_DIR}")
        return

    files = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".m3u")]
    if not files:
        print(f"❌ {SOURCE_DIR} 中没有找到任何 .m3u 文件")
        return

    print(f"📂 检测到 {len(files)} 个 M3U 文件，开始合并…")

    for file in files:
        path = os.path.join(SOURCE_DIR, file)
        entries = parse_m3u(path)
        print(f"✅ 解析 {file}：{len(entries)} 条记录")

        for name, url, logo, group in entries:
            key = normalize_name(name) + "|" + url
            if key not in seen:
                seen.add(key)
                all_entries.append((name, url, logo, group, file))

    print(f"📊 合并后共 {len(all_entries)} 条唯一频道记录")

    # 写入 M3U
    with open(MERGED_M3U, "w", encoding="utf-8") as m3u:
        m3u.write("#EXTM3U\n")
        for name, url, logo, group, src in all_entries:
            m3u.write(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}\n{url}\n')
    print(f"💾 已生成合并 M3U：{MERGED_M3U}")

    # 写入 CSV
    with open(MERGED_CSV, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["频道名", "播放地址", "LOGO", "分组", "来源文件"])
        writer.writerows(all_entries)
    print(f"💾 已生成合并 CSV：{MERGED_CSV}")

    print(f"🏁 合并完成，共 {len(all_entries)} 条记录。时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    merge_all_sources()