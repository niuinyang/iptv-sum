import os
import re
import csv
import unicodedata

# ==============================
# 配置区
# ==============================
SOURCE_DIR = "input/network/network_sources"  # 下载源目录
ICON_DIR = "png"                              # 本地图标目录
OUTPUT_DIR = "output"
LOG_DIR = os.path.join(OUTPUT_DIR, "log")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

OUTPUT_M3U = os.path.join(OUTPUT_DIR, "merge_total.m3u")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "merge_total.csv")
SKIPPED_LOG = os.path.join(LOG_DIR, "skipped.log")

# ==============================
# 工具函数
# ==============================
def normalize_channel_name(name: str) -> str:
    """标准化频道名（去掉符号、空格、统一大小写）"""
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r"[\s\[\]（）()【】]", "", name)
    name = re.sub(r"[-_\.]", "", name)
    return name.strip().lower()


def get_icon_path(name: str) -> str:
    """获取图标路径（本地优先，否则用远程链接）"""
    local_path = os.path.join(ICON_DIR, f"{name}.png")
    if os.path.exists(local_path):
        return local_path
    encoded_name = re.sub(r"\s+", "", name)
    return f"https://epg.pw/media/logo/{encoded_name}.png"


def read_m3u_file(file_path: str):
    """读取 M3U 文件，返回 (频道名, URL) 列表"""
    channels = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("#EXTINF:"):
                info_line = line
                url_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                match = re.search(r'tvg-name="([^"]+)"', info_line)
                name = match.group(1) if match else "未知频道"
                channels.append((name, url_line))
                i += 2
            else:
                i += 1

        print(f"📡 已加载 {os.path.basename(file_path)}: {len(channels)} 条频道")
        return channels

    except Exception as e:
        print(f"⚠️ 读取 {file_path} 失败: {e}")
        return []


# ==============================
# 主逻辑（去重相同 URL）
# ==============================
def merge_local_sources():
    all_channels = []
    skipped = []
    seen_urls = set()

    print(f"📂 正在读取文件夹: {os.path.abspath(SOURCE_DIR)}")

    for file in os.listdir(SOURCE_DIR):
        if not file.endswith(".m3u"):
            continue
        file_path = os.path.join(SOURCE_DIR, file)
        channels = read_m3u_file(file_path)

        for name, url in channels:
            if not url.startswith("http"):
                skipped.append((name, url))
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            all_channels.append((name, url))

    print(f"\n✅ 合并完成：共 {len(all_channels)} 条频道（已去重相同 URL）")

    # ==============================
    # 写入 M3U（tvg-name 用标准化名）
    # ==============================
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, url in all_channels:
            normalized = normalize_channel_name(name)
            logo = get_icon_path(name)
            f.write(f'#EXTINF:-1 tvg-name="{normalized}" tvg-logo="{logo}",{name}\n{url}\n')

    # ==============================
    # 写入 CSV（列顺序符合要求）
    # ==============================
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["normalized_name", "", "URL", "来源", "tvg-name", "icon_url"])
        for name, url in all_channels:
            normalized = normalize_channel_name(name)
            icon = get_icon_path(name)
            writer.writerow([normalized, "", url, "网络源", name, icon])

    # ==============================
    # 写入跳过日志
    # ==============================
    with open(SKIPPED_LOG, "w", encoding="utf-8") as f:
        for name, url in skipped:
            f.write(f"{name},{url}\n")

    print(f"📁 M3U 输出: {OUTPUT_M3U}")
    print(f"📁 CSV 输出: {OUTPUT_CSV}")
    print(f"📁 跳过日志: {SKIPPED_LOG}")
    print("✅ 所有文件生成完成！")


# ==============================
# 主入口
# ==============================
if __name__ == "__main__":
    merge_local_sources()