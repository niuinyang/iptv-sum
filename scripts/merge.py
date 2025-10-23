import os
import re
import requests
import time

SOURCES_FILE = "input/network/networksource.txt"
OUTPUT_FILE = "output/total.m3u"
os.makedirs("output", exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}
RETRY_TIMES = 3
TIMEOUT = 15

def fetch_sources(file_path):
    all_lines = []
    success, failed = 0, 0

    with open(file_path, "r", encoding="utf-8") as f:
        urls = [u.strip() for u in f if u.strip() and not u.strip().startswith("#")]

    for url in urls:
        print(f"📡 Fetching: {url}")
        try:
            if url.startswith("http"):
                text = None
                for attempt in range(RETRY_TIMES):
                    try:
                        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                        r.encoding = r.apparent_encoding or "utf-8"
                        text = r.text
                        break
                    except Exception as e:
                        print(f"⚠️ 重试 {attempt+1}/{RETRY_TIMES} 失败: {e}")
                        time.sleep(2)
                if text is None:
                    raise Exception("多次请求失败")
            else:
                with open(url, encoding="utf-8", errors="ignore") as f_local:
                    text = f_local.read()

            # 每个源只去掉一次 #EXTM3U
            lines = text.splitlines()
            filtered_lines = []
            removed_header = False
            for l in lines:
                l_strip = l.strip()
                if l_strip.startswith("#EXTM3U") and not removed_header:
                    removed_header = True
                    continue
                if l_strip:
                    filtered_lines.append(l_strip)

            all_lines.extend(filtered_lines)
            success += 1
        except Exception as e:
            failed += 1
            print(f"❌ Failed: {url} ({e})")

    return all_lines, success, failed

def parse_channels(lines):
    url_pattern = re.compile(r'^https?://')
    pairs = []

    for i, line in enumerate(lines):
        if line.startswith("#EXTINF"):
            # 向下找第一个 URL
            for j in range(i+1, len(lines)):
                next_line = lines[j].strip()
                if url_pattern.match(next_line):
                    pairs.append((line, next_line))
                    break
    return pairs

def deduplicate(pairs):
    seen = set()
    unique_pairs = []
    for title, url in pairs:
        key = (title, url)
        if key not in seen:
            unique_pairs.append((title, url))
            seen.add(key)
    return unique_pairs

def natural_sort_key(text):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"([0-9]+)", text)]

def write_m3u(pairs, output_file):
    pairs.sort(key=lambda x: natural_sort_key(x[0]))
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, url in pairs:
            f.write(f"{title}\n{url}\n")

if __name__ == "__main__":
    all_lines, success, failed = fetch_sources(SOURCES_FILE)
    pairs = parse_channels(all_lines)
    unique_pairs = deduplicate(pairs)
    write_m3u(unique_pairs, OUTPUT_FILE)

    print(f"\n✅ 合并完成：成功 {success} 源，失败 {failed} 源，"
          f"去重后 {len(unique_pairs)} 条频道 → {OUTPUT_FILE}")
