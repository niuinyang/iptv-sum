import requests, os, time, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean
from collections import defaultdict

# ==============================
# 配置区
# ==============================
input_file = "output/total.m3u"
output_file = "output/working.m3u"
progress_file = "output/progress.json"
skipped_file = "output/skipped.txt"
os.makedirs("output", exist_ok=True)

TIMEOUT = 10
BASE_THREADS = 50
MAX_THREADS = 200
HEADERS = {"User-Agent": "Mozilla/5.0"}

# 过滤规则
LOW_RES_KEYWORDS = ["SD", "VGA", "480p", "576p"]
BLOCK_KEYWORDS = ["espanol"]

DEBUG = False

# ==============================
# 工具函数
# ==============================
def is_high_res(title):
    return not any(kw.lower() in title.lower() for kw in LOW_RES_KEYWORDS)

def is_allowed(title, url):
    if not is_high_res(title):
        return False
    for kw in BLOCK_KEYWORDS:
        if kw.lower() in title.lower() or kw.lower() in url.lower():
            return False
    return True

def quick_check(url):
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code < 400 and (
            "video" in r.headers.get("content-type", "").lower()
            or url.lower().endswith((".m3u8", ".ts", ".mp4"))
        ):
            return True
    except Exception:
        pass
    return False

def deep_check(url):
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=TIMEOUT, allow_redirects=True)
        real_url = r.url.lower()

        # 若跳转到了视频格式
        if real_url.endswith((".m3u8", ".ts", ".mp4")):
            return True

        # 检查内容头
        text_head = r.text[:1024]
        if "#EXTM3U" in text_head:
            return True

        # 检查视频流字节特征
        for _ in range(10):
            chunk = next(r.iter_content(chunk_size=8192), b'')
            if any(sig in chunk for sig in [b"mpegts", b"ftyp", b"\x00\x00\x01\xb3"]):
                return True
            if not chunk:
                break
    except Exception as e:
        if DEBUG:
            with open(skipped_file, "a", encoding="utf-8") as f:
                f.write(f"DEEP_CHECK_EXCEPTION -> {url} ({e})\n")
    return False

def check_stream(title, url):
    start = time.time()
    if quick_check(url) or deep_check(url):
        elapsed = time.time() - start
        return True, elapsed
    return False, None

# ==============================
# 主逻辑
# ==============================
def load_progress():
    return json.load(open(progress_file)) if os.path.exists(progress_file) else {}

def save_progress(done):
    json.dump(done, open(progress_file, "w"))

def load_pairs():
    lines = open(input_file, encoding="utf-8").read().splitlines()
    pairs = []
    for i in range(0, len(lines)-1):
        if lines[i].startswith("#EXTINF") and lines[i+1].startswith("http"):
            title, url = lines[i], lines[i+1]
            if is_allowed(title, url):
                pairs.append((title, url))
    return pairs

def group_by_channel(pairs):
    grouped = defaultdict(list)
    for title, url in pairs:
        name = title.split(",")[-1].strip().lower()
        grouped[name].append((title, url))
    return grouped

def test_all():
    pairs = load_pairs()
    done = load_progress()
    print(f"待检测源数：{len(pairs)}")

    results = []
    with ThreadPoolExecutor(max_workers=BASE_THREADS) as executor:
        future_to_pair = {executor.submit(check_stream, t, u): (t, u) for t, u in pairs if u not in done}
        for future in as_completed(future_to_pair):
            title, url = future_to_pair[future]
            try:
                ok, elapsed = future.result()
                if ok:
                    results.append((title, url, elapsed))
                    done[url] = elapsed
                    print(f"✅ {title.split(',')[-1]} ({elapsed:.2f}s)")
                else:
                    print(f"❌ {title.split(',')[-1]}")
            except Exception as e:
                print(f"⚠️ {url} -> {e}")
            finally:
                save_progress(done)
    return results

def save_results(results):
    grouped = defaultdict(list)
    for title, url, elapsed in results:
        name = title.split(",")[-1].strip().lower()
        grouped[name].append((title, url, elapsed))

    with open(output_file, "w", encoding="utf-8") as f:
        for name, items in grouped.items():
            sorted_items = sorted(items, key=lambda x: x[2])
            for title, url, _ in sorted_items:
                f.write(f"{title}\n{url}\n")

    print(f"\n✅ 检测完成，共 {len(results)} 条有效源，已写入 {output_file}")

if __name__ == "__main__":
    results = test_all()
    save_results(results)