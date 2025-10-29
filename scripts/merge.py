import os
import re
import csv
import requests
from collections import defaultdict

# ==============================
# 配置路径
# ==============================
SOURCES_FILE = "input/network/networksource.txt"  # 每行一个源地址（本地文件或 URL）
OUTPUT_DIR = "output"
LOG_DIR = os.path.join(OUTPUT_DIR, "log")
MIDDLE_DIR = os.path.join(OUTPUT_DIR, "middle")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(MIDDLE_DIR, exist_ok=True)

OUTPUT_M3U = os.path.join(OUTPUT_DIR, "merge_total.m3u")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "total.csv")
SKIPPED_FILE = os.path.join(LOG_DIR, "skipped.log")

HEADERS = {"User-Agent": "Mozilla/5.0"}
RETRY_TIMES = 3
TIMEOUT = 15

# ==============================
# 获取源文件内容（增强版）
# ==============================
def fetch_sources(file_path):
    all_lines = []
    success, failed = 0, 0

    with open(file_path, "r", encoding="utf-8") as f:
        urls = [u.strip() for u in f if u.strip() and not u.startswith("#")]

    for url in urls:
        print(f"📡 Fetching: {url}")
        try:
            if url.startswith("http"):
                text = None
                for attempt in range(RETRY_TIMES):
                    try:
                        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                        r.raise_for_status()
                        # 尝试多种编码
                        for enc in [r.encoding, r.apparent_encoding, "utf-8", "utf-8-sig", "latin1"]:
                            try:
                                text = r.content.decode(enc)
                                break
                            except:
                                continue
                        if text is None:
                            raise Exception("无法解码内容")

                        # 简单过滤 HTML 页面
                        if "<html" in text.lower() and "<body" in text.lower():
                            raise Exception("内容疑似 HTML 页面，非 M3U")

                        break
                    except Exception as e:
                        print(f"⚠️ Retry {attempt+1}/{RETRY_TIMES} failed: {e}")
                if text is None:
                    raise Exception("Failed after retries")
            else:
                # 本地文件尝试多种编码
                text = None
                for enc in ["utf-8", "utf-8-sig", "latin1"]:
                    try:
                        with open(url, encoding=enc, errors="ignore") as f_local:
                            text = f_local.read()
                        break
                    except Exception as e:
                        continue
                if text is None:
                    raise Exception("无法读取本地文件")

            # 拆行
            lines = text.splitlines()
            print(f"源 {url} 共 {len(lines)} 行，前 5 行预览: {lines[:5]}")

            # 去掉 #EXTM3U
            filtered_lines = []
            removed_header = False
            for l in lines:
                l_strip = l.strip()
                if l_strip.startswith("#EXTM3U") and not removed_header:
                    removed_header = True
                    continue
                if l_strip:
                    filtered_lines.append(l_strip)

            print(f"过滤后 {len(filtered_lines)} 行")
            all_lines.extend(filtered_lines)
            success += 1
        except Exception as e:
            failed += 1
            with open(SKIPPED_FILE, "a", encoding="utf-8") as f_log:
                f_log.write(f"❌ Failed: {url} ({e})\n")
            print(f"❌ Failed: {url} ({e})")

    return all_lines, success, failed

# ==============================
# 解析 EXTINF + URL 对
# ==============================
def parse_channels(lines):
    pairs = []
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            # 向下找第一个 URL
            for j in range(i+1, len(lines)):
                url_line = lines[j].strip()
                if url_line.startswith("http"):
                    pairs.append((line, url_line))
                    break
    return pairs

# ==============================
# 去重 EXTINF + URL
# ==============================
def deduplicate(pairs):
    seen = set()
    unique_pairs = []
    for title, url in pairs:
        key = (title, url)
        if key not in seen:
            unique_pairs.append((title, url))
            seen.add(key)
    return unique_pairs

# ==============================
# 自然排序
# ==============================
def natural_sort_key(text):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"([0-9]+)", text)]

# ==============================
# 分组排序
# ==============================
def group_sort(pairs):
    group_dict = defaultdict(list)
    group_pattern = re.compile(r'group-title="([^"]*)"')

    for title, url in pairs:
        match = group_pattern.search(title)
        group_name = match.group(1).strip() if match else "未分类"
        group_dict[group_name].append((title, url))

    # 分组排序，组内自然排序
    sorted_pairs = []
    for group in sorted(group_dict.keys()):
        group_items = group_dict[group]
        group_items.sort(key=lambda x: natural_sort_key(x[0]))
        sorted_pairs.extend(group_items)
    return sorted_pairs

# ==============================
# 写入 total.m3u
# ==============================
def write_m3u(pairs, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, url in pairs:
            f.write(f"{title}\n{url}\n")

# ==============================
# 写入 CSV
# ==============================
def write_csv(pairs, csv_file):
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "url"])
        for title, url in pairs:
            writer.writerow([title, url])

# ==============================
# 主流程
# ==============================
if __name__ == "__main__":
    # 清空日志
    if os.path.exists(SKIPPED_FILE):
        os.remove(SKIPPED_FILE)

    all_lines, success, failed = fetch_sources(SOURCES_FILE)
    if not all_lines:
        print("⚠️ 没有抓取到任何内容，请检查 networksource.txt 或网络连接")
    parsed_pairs = parse_channels(all_lines)

    # 写入中间 CSV/M3U 文件
    write_csv(parsed_pairs, os.path.join(MIDDLE_DIR, "parsed.csv"))
    write_m3u(parsed_pairs, os.path.join(MIDDLE_DIR, "parsed.m3u"))

    unique_pairs = deduplicate(parsed_pairs)
    grouped_sorted_pairs = group_sort(unique_pairs)

    write_m3u(grouped_sorted_pairs, OUTPUT_M3U)
    write_csv(grouped_sorted_pairs, OUTPUT_CSV)

    print(f"\n✅ 合并完成：成功 {success} 源，失败 {failed} 源，"
          f"去重后 {len(grouped_sorted_pairs)} 条频道 → {OUTPUT_M3U} / {OUTPUT_CSV}")
    print(f"📁 中间文件 → {MIDDLE_DIR}")
    print(f"📁 日志文件 → {SKIPPED_FILE}")