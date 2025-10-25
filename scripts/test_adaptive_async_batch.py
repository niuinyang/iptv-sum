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
os.makedirs("output", exist_ok=True)

TIMEOUT = 10
BASE_THREADS = 50
MAX_THREADS = 200
BATCH_SIZE = 300

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
    "Accept": "*/*",
    "Connection": "keep-alive",
}

# ==============================
# 低分辨率和关键字过滤
# ==============================
LOW_RES_KEYWORDS = ["SD", "VGA", "480p", "576p"]
BLOCK_KEYWORDS = ["espanol"]  # 不检测这些关键字

def is_high_res(title):
    return not any(kw.lower() in title.lower() for kw in LOW_RES_KEYWORDS)

def is_allowed(title, url):
    """是否允许检测：高清且不含黑名单关键字"""
    if not is_high_res(title):
        return False
    for kw in BLOCK_KEYWORDS:
        if kw.lower() in title.lower() or kw.lower() in url.lower():
            return False
    return True

# ==============================
# 检测函数
# ==============================
def quick_check(url):
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code < 400 and (
            "video" in r.headers.get("content-type", "").lower()
            or url.lower().endswith((".m3u8", ".ts"))
        ):
            return True
    except:
        pass
    return False

def deep_check(url):
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=TIMEOUT)
        for _ in range(3):
            chunk = next(r.iter_content(chunk_size=8192), b'')
            if any(sig in chunk for sig in [
                b"#EXTM3U", b"mpegts", b"ftyp", b"\x00\x00\x01\xb3", b"HTTP Live Streaming"
            ]):
                return True
            if not chunk:
                break
    except:
        pass
    return False

def test_stream(url):
    start = time.time()
    ok = quick_check(url) or deep_check(url)
    elapsed = round(time.time() - start, 3)
    return ok, elapsed

def detect_optimal_threads():
    test_urls = [
        "https://www.apple.com",
        "https://www.google.com",
        "https://www.microsoft.com",
    ]
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
# 读取 M3U 并生成 (title, url) 对
# ==============================
lines = open(input_file, encoding="utf-8").read().splitlines()
pairs = []
i = 0
while i < len(lines):
    if lines[i].startswith("#EXTINF") and i + 1 < len(lines):
        title, url = lines[i], lines[i+1]
        if is_allowed(title, url):
            pairs.append((title, url))
        i += 2
    else:
        i += 1

# ==============================
# 恢复进度
# ==============================
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
print(f"🚀 开始检测 {total} 条符合条件的流（每批 {BATCH_SIZE} 条）")

start_time = time.time()
all_working = []

# ==============================
# 批量检测
# ==============================
for batch_start in range(done_index, total, BATCH_SIZE):
    batch = pairs[batch_start: batch_start + BATCH_SIZE]
    working_batch = []

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(test_stream, url): (title, url) for title, url in batch}
        for future in as_completed(futures):
            title, url = futures[future]
            try:
                ok, elapsed = future.result()
                if ok:
                    working_batch.append((title, url, elapsed))
            except:
                pass

    all_working.extend(working_batch)

    # 更新进度文件
    json.dump({"done": min(batch_start + BATCH_SIZE, total)}, open(progress_file, "w", encoding="utf-8"))

    print(f"🧮 本批完成：{len(working_batch)}/{len(batch)} 可用流 | 已完成 {min(batch_start + BATCH_SIZE, total)}/{total}")

# 删除进度文件
if os.path.exists(progress_file):
    os.remove(progress_file)

# ==============================
# 按频道分组并按响应速度排序
# ==============================
grouped = defaultdict(list)
for title, url, elapsed in all_working:
    # 尝试提取频道名
    m = re.search(r'[,](.+)$', title)
    channel_name = m.group(1).strip() if m else title
    grouped[channel_name].append((title, url, elapsed))

# 组内按响应速度排序
for name in grouped:
    grouped[name].sort(key=lambda x: x[2])

# 写入输出文件
with open(output_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for name in sorted(grouped.keys()):  # 按频道名排序
        for title, url, _ in grouped[name]:
            f.write(f"{title}\n{url}\n")

elapsed_total = round(time.time() - start_time, 2)
print(f"✅ 检测完成，共 {len(all_working)} 条可用高清及以上流，用时 {elapsed_total} 秒")