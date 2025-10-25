import requests, os, time, json, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean
from collections import defaultdict
import multiprocessing

# ==============================
# 配置区
# ==============================
input_file = "output/total.m3u"
output_file = "output/working.m3u"
progress_file = "output/progress.json"
skipped_file = "output/skipped.log"
suspect_file = "output/suspect.log"
os.makedirs("output", exist_ok=True)

TIMEOUT = 15
BASE_THREADS = 50
MAX_THREADS = 200
BATCH_SIZE = 300
DEBUG = True

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive",
}

LOW_RES_KEYWORDS = ["SD", "VGA", "480p", "576p"]
BLOCK_KEYWORDS = ["espanol"]

# ==============================
# 过滤规则
# ==============================
def is_high_res(title):
    return not any(re.search(rf'\b{kw}\b', title, re.IGNORECASE) for kw in LOW_RES_KEYWORDS)

def is_allowed(title, url):
    text = title + " " + url
    if not is_high_res(title):
        log_skip("LOW_RES", title, url)
        return False
    for kw in BLOCK_KEYWORDS:
        if re.search(rf'\b{kw}\b', text, re.IGNORECASE):
            log_skip("BLOCK_KEYWORD", title, url)
            return False
    return True

def log_skip(reason, title, url):
    if DEBUG:
        with open(skipped_file, "a", encoding="utf-8") as f:
            f.write(f"{reason} -> {title}\n{url}\n")

def log_suspect(reason, url):
    with open(suspect_file, "a", encoding="utf-8") as f:
        f.write(f"{reason} -> {url}\n")

# ==============================
# 检测逻辑
# ==============================
def is_video_content(r, url):
    """判断响应是否为视频流"""
    ctype = r.headers.get("content-type", "").lower()
    video_types = [
        "video/", "mpegurl", "x-mpegurl",
        "application/vnd.apple.mpegurl", "application/x-mpegurl",
        "application/octet-stream"
    ]
    if any(v in ctype for v in video_types):
        return True
    if url.lower().endswith((".m3u8", ".ts", ".mp4", ".mov")):
        return True
    return False

def quick_check(url):
    """HEAD 快速检测"""
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code < 400 and is_video_content(r, r.url):
            return True, r.url
    except Exception:
        pass
    return False, url

def deep_check(url):
    """GET 检测，支持中转地址"""
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=TIMEOUT, allow_redirects=True)
        real_url = r.url.lower()
        if is_video_content(r, real_url):
            return True, real_url

        # 检查 .ctv / .php / .html 页面中是否有视频跳转
        text = r.text[:2048]
        if "#EXTM3U" in text:
            return True, real_url
        if "m3u8" in text or ".ts" in text:
            log_suspect("HTML_HAS_STREAM_LINK", url)
            return True, real_url

        # 检查字节特征
        for _ in range(5):
            chunk = next(r.iter_content(chunk_size=8192), b'')
            if any(sig in chunk for sig in [b"mpegts", b"ftyp", b"\x00\x00\x01\xb3"]):
                return True, real_url
            if not chunk:
                break
    except Exception as e:
        if DEBUG:
            log_skip("DEEP_CHECK_EXCEPTION", url, str(e))
    return False, url

def test_stream(url):
    """检测流可用性"""
    start = time.time()
    ok, final_url = quick_check(url)
    if not ok:
        ok, final_url = deep_check(url)
    elapsed = round(time.time() - start, 3)
    return ok, elapsed, final_url

def detect_optimal_threads():
    """动态线程数"""
    test_urls = ["https://www.apple.com", "https://www.google.com", "https://www.microsoft.com"]
    times = []
    for u in test_urls:
        t0 = time.time()
        try:
            requests.head(u, timeout=TIMEOUT)
        except:
            pass
        times.append(time.time() - t0)
    avg = mean(times)
    cpu_threads = multiprocessing.cpu_count() * 5
    if avg < 0.5:
        return min(MAX_THREADS, cpu_threads)
    elif avg < 1:
        return min(150, cpu_threads)
    elif avg < 2:
        return min(100, cpu_threads)
    else:
        return BASE_THREADS

# ==============================
# 主逻辑
# ==============================
lines = open(input_file, encoding="utf-8").read().splitlines()
pairs = []
i = 0
while i < len(lines):
    if lines[i].startswith("#EXTINF") and i + 1 < len(lines):
        title, url = lines[i], lines[i + 1]
        if is_allowed(title, url):
            pairs.append((title, url))
        else:
            print(f"🚫 跳过: {title}")
        i += 2
    else:
        i += 1

done_index = 0
if os.path.exists(progress_file):
    try:
        done_index = json.load(open(progress_file, encoding="utf-8")).get("done", 0)
        print(f"🔄 恢复进度，从第 {done_index} 条继续")
    except:
        pass

total = len(pairs)
threads = detect_optimal_threads()
print(f"⚙️ 动态并发线程数：{threads}")
print(f"🚀 开始检测 {total} 条流（每批 {BATCH_SIZE} 条）")

start_time = time.time()
all_working = []

for batch_start in range(done_index, total, BATCH_SIZE):
    batch = pairs[batch_start: batch_start + BATCH_SIZE]
    working_batch = []
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(test_stream, url): (title, url) for title, url in batch}
        for future in as_completed(futures):
            title, url = futures[future]
            try:
                ok, elapsed, final_url = future.result()
                if ok:
                    working_batch.append((title, final_url, elapsed))
                    print(f"✅ {title.split(',')[-1].strip()} ({elapsed}s)")
                else:
                    log_skip("FAILED_CHECK", title, url)
            except Exception as e:
                log_skip("EXCEPTION", title, url)
    all_working.extend(working_batch)
    json.dump({"done": min(batch_start + BATCH_SIZE, total)}, open(progress_file, "w", encoding="utf-8"))
    print(f"🧮 本批完成：{len(working_batch)}/{len(batch)} 可用流 | 已完成 {min(batch_start + BATCH_SIZE, total)}/{total}")

if os.path.exists(progress_file):
    os.remove(progress_file)

# ==============================
# 分组、排序、去重
# ==============================
grouped = defaultdict(list)
for title, url, elapsed in all_working:
    m = re.search(r'[,](.+)$', title)
    name = m.group(1).strip().lower() if m else title.lower()
    grouped[name].append((title, url, elapsed))

# 每组按速度排序，去重保留最快源
with open(output_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for name in sorted(grouped.keys()):
        group_sorted = sorted(grouped[name], key=lambda x: x[2])
        title, url, _ = group_sorted[0]
        f.write(f"{title}\n{url}\n")

elapsed_total = round(time.time() - start_time, 2)
print(f"\n✅ 检测完成，共 {len(all_working)} 条可用高清流，用时 {elapsed_total} 秒")
print(f"📁 可用源: {output_file}")
print(f"⚠️ 失败或过滤源: {skipped_file}")
print(f"🕵️ 可疑误杀源: {suspect_file}")