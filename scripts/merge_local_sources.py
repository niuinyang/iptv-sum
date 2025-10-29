import os
import csv
import re
from collections import defaultdict

# ==============================
# 绝对路径配置
# ==============================
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(ROOT_DIR, "input/network/network_sources")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")
LOG_DIR = os.path.join(OUTPUT_DIR, "log")

MERGE_M3U = os.path.join(OUTPUT_DIR, "merge_total.m3u")
MERGE_CSV = os.path.join(OUTPUT_DIR, "merge_total.csv")
SKIP_LOG = os.path.join(LOG_DIR, "skipped.log")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ==============================
# 功能函数
# ==============================

def normalize_channel_name(name: str) -> str:
    """标准化频道名"""
    name = re.sub(r'\s*\(.*?\)|\[.*?\]', '', name)
    name = re.sub(r'[^0-9A-Za-z\u4e00-\u9fa5]+', '', name)
    return name.strip().lower()

def parse_m3u(file_path):
    """解析 M3U 文件为频道列表"""
    channels = []
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF:"):
                info = lines[i].strip()
                url = lines[i + 1].strip() if i + 1 < len(lines) else ""
                name_match = re.search(r',(.+)$', info)
                name = name_match.group(1).strip() if name_match else "未知频道"
                channels.append((name, url))
    except Exception as e:
        print(f"❌ 解析失败: {file_path} ({e})")
    return channels

# ==============================
# 主逻辑
# ==============================

def main():
    all_channels = defaultdict(set)
    skipped = []

    print(f"📂 正在读取文件夹: {SOURCE_DIR}")

    for file in os.listdir(SOURCE_DIR):
        if not file.endswith(".m3u"):
            continue
        path = os.path.join(SOURCE_DIR, file)
        channels = parse_m3u(path)
        print(f"📡 已加载 {file}: {len(channels)} 条频道")
        for name, url in channels:
            norm_name = normalize_channel_name(name)
            if not url.startswith("http"):
                skipped.append((name, url))
                continue
            all_channels[norm_name].add((name, url))

    merged_channels = []
    for ch_name, items in all_channels.items():
        # 取第一个非空源
        for name, url in items:
            merged_channels.append((name, url))
            break

    # 输出 M3U
    with open(MERGE_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, url in merged_channels:
            f.write(f"#EXTINF:-1,{name}\n{url}\n")

    # 输出 CSV
    with open(MERGE_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "url"])
        for name, url in merged_channels:
            writer.writerow([name, url])

    # 跳过日志
    with open(SKIP_LOG, "w", encoding="utf-8") as f:
        for name, url in skipped:
            f.write(f"{name} | {url}\n")

    print(f"\n✅ 合并完成：共 {len(merged_channels)} 条频道")
    print(f"📁 输出 M3U: {MERGE_M3U}")
    print(f"📁 输出 CSV: {MERGE_CSV}")
    print(f"📁 跳过日志: {SKIP_LOG}")

if __name__ == "__main__":
    main()