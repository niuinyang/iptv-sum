import os
import re
import csv
import unicodedata
import requests

# ==============================
# 配置区
# ==============================
SOURCE_DIR = "input/network/network_sources"  # M3U 文件所在目录
OUTPUT_DIR = "output"
LOG_DIR = os.path.join(OUTPUT_DIR, "log")
ICON_DIR = "png"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(ICON_DIR, exist_ok=True)

OUTPUT_M3U = os.path.join(OUTPUT_DIR, "merge_total.m3u")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "merge_total.csv")
SKIPPED_LOG = os.path.join(LOG_DIR, "skipped.log")

# ==============================
# 工具函数
# ==============================

def normalize_channel_name(name: str) -> str:
    """标准化频道名（去除空白符号、大小写统一等）"""
    if not name:
        return ""
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r"[\s\[\]（）()【】]", "", name)
    name = re.sub(r"[-_\.]", "", name)
    return name.strip().lower()

def download_icon(url, local_path):
    try:
        if not os.path.exists(local_path):
            print(f"🔽 下载图标：{url} -> {local_path}")
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                with open(local_path, "wb") as f:
                    f.write(resp.content)
            else:
                print(f"⚠️ 下载失败，状态码: {resp.status_code}")
        # 已存在则不下载
        return local_path
    except Exception as e:
        print(f"⚠️ 下载图标异常: {e}")
        return ""

def get_icon_path(standard_name, tvg_logo_url):
    ext = ".png"  # 默认扩展名
    if tvg_logo_url:
        # 尝试从 URL 中提取后缀
        clean_url = tvg_logo_url.split("?")[0]
        if "." in clean_url:
            ext_candidate = clean_url.split("/")[-1].split(".")[-1]
            if ext_candidate.lower() in ["png", "jpg", "jpeg", "gif", "bmp", "webp"]:
                ext = "." + ext_candidate.lower()

    local_icon_path = os.path.join(ICON_DIR, standard_name + ext)

    if os.path.exists(local_icon_path):
        return local_icon_path
    else:
        if tvg_logo_url:
            downloaded_path = download_icon(tvg_logo_url, local_icon_path)
            return downloaded_path
        else:
            return ""

def read_m3u_file(file_path: str):
    """
    读取 M3U 文件，返回频道列表，每项是 dict：
    {
      'tvg_name': (tvg-name字段，可能None),
      'display_name': (逗号后显示名),
      'url': 播放地址,
      'logo': 本地图标路径
    }
    """
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

                tvg_match = re.search(r'tvg-name=[\'"]([^\'"]+)[\'"]', info_line)
                tvg_name = tvg_match.group(1).strip() if tvg_match else None

                logo_match = re.search(r'tvg-logo=[\'"]([^\'"]+)[\'"]', info_line)
                tvg_logo_url = logo_match.group(1).strip() if logo_match else ""

                if "," in info_line:
                    display_name = info_line.split(",", 1)[1].strip()
                else:
                    display_name = "未知频道"

                standard_name = normalize_channel_name(tvg_name or display_name)

                icon_path = get_icon_path(standard_name, tvg_logo_url)

                channels.append({
                    "tvg_name": tvg_name,
                    "display_name": display_name,
                    "url": url_line,
                    "logo": icon_path
                })
                i += 2
            else:
                i += 1

        print(f"📡 已加载 {os.path.basename(file_path)}: {len(channels)} 条频道")
        return channels

    except Exception as e:
        print(f"⚠️ 读取 {file_path} 失败: {e}")
        return []

def write_output_files(channels):
    seen_urls = set()
    valid_channels = []
    skipped_channels = []

    for ch in channels:
        url = ch["url"]
        if not url.startswith("http"):
            skipped_channels.append(ch)
            continue
        if url in seen_urls:
            skipped_channels.append(ch)
            continue
        seen_urls.add(url)
        valid_channels.append(ch)

    print(f"\n✅ 过滤有效频道: {len(valid_channels)} 条，有效 URL 去重后")
    print(f"跳过无效或重复频道: {len(skipped_channels)} 条")

    # 写 M3U，tvg-name 用标准化名，频道显示名用 display_name
    with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in valid_channels:
            tvg_name_norm = normalize_channel_name(ch["tvg_name"] or ch["display_name"])
            display_name = ch["display_name"]
            url = ch["url"]
            f.write(f'#EXTINF:-1 tvg-name="{tvg_name_norm}",{display_name}\n{url}\n')

    # 写 CSV，第一列标准化名，第二列空，第三列 URL，第四列固定“网络源”，第五列原频道名，第六列图标路径
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["standard_name", "", "url", "source", "original_name", "logo"])
        for ch in valid_channels:
            standard_name = normalize_channel_name(ch["tvg_name"] or ch["display_name"])
            writer.writerow([standard_name, "", ch["url"], "网络源", ch["display_name"], ch.get("logo", "")])

    # 写跳过日志
    with open(SKIPPED_LOG, "w", encoding="utf-8") as f:
        for ch in skipped_channels:
            f.write(f"{ch['display_name']},{ch['url']}\n")

    print(f"📁 输出文件：{OUTPUT_M3U} 和 {OUTPUT_CSV}")
    print(f"📁 跳过日志：{SKIPPED_LOG}")

def merge_all_sources():
    all_channels = []
    if not os.path.exists(SOURCE_DIR):
        print(f"⚠️ 源目录不存在: {SOURCE_DIR}")
        return []

    print(f"📂 扫描目录: {SOURCE_DIR}")
    for file in os.listdir(SOURCE_DIR):
        if file.endswith(".m3u"):
            file_path = os.path.join(SOURCE_DIR, file)
            chs = read_m3u_file(file_path)
            all_channels.extend(chs)

    print(f"\n📊 合并所有频道，共 {len(all_channels)} 条")
    return all_channels

if __name__ == "__main__":
    channels = merge_all_sources()
    if channels:
        write_output_files(channels)
    else:
        print("⚠️ 没有读取到任何频道")