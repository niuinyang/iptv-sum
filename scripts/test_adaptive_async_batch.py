import requests, os, time, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean

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
# 检测函数
# ==============================
def quick_check(url):
    """第一层：HEAD 请求检测"""
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code < 400 and (
            "video" in r.headers.get("content-type", "").lower()
            or url.lower().endswith((".m3u8", ".ts"))
        ):
            return True
    except Exception:
        pass
    return False


def deep_check(url):
    """第二层：下载前几 KB 验证是否为视频流"""
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=TIMEOUT)
        chunk = next(r.iter_content(chunk_size=8192))
        if any(sig in chunk for sig in [
            b"#EXTM3U", b"mpegts", b"ftyp", b"\x00\x00\x01\xb3", b"HTTP Live Streaming"
        ]):
            return True
    except Exception:
        pass
    return False


def test_stream(url):
    """综合检测：HEAD 失败则尝试 GET"""
    return quick_check(url) or deep_check(url)


def detect_optimal_threads():
    """根据网络延迟动态调整线程数"""
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
    if avg < 0.5:
        return MAX_THREADS
    elif avg < 1:
        return 150
    elif avg < 2:
        return 100
    else:
        return BASE_THREADS


# ==============================
# 主逻辑
# ==============================
lines = open(input_file, encoding="utf-8").read().splitlines()
pairs = [(lines[i], lines[i+1]) for i in range(len(lines)-1) if lines[i].startswith("#EXTINF")]

done_index = 0
if os.path.exists(progress_file):
    try:
        done_index = json.load(open(progress_file, encoding="utf-8")).get("done", 0)
        print(f"🔄 恢复进度，从第 {done_index} 条继续")
    except:
        pass

working = ["#EXTM3U"]
total = len(pairs)
threads = detect_optimal_threads()
print(f"⚙️ 动态并发线程数：{threads}")
print(f"🚀 开始检测 {total} 条流（每批 {BATCH_SIZE} 条）")

start_time = time.time()

for batch_start in range(done_index, total, BATCH_SIZE):
    batch = pairs[batch_start: batch_start + BATCH_SIZE]
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(test_stream, url): (title, url) for title, url in batch}
        for future in as_completed(futures):
            title, url = futures[future]
            try:
                ok = future.result()
                if ok:
                    working.append(title)
                    working.append(url)
                    print(f"✅ {url}")
                else:
                    print(f"❌ {url}")
            except Exception as e:
                print(f"❌ Error: {url} ({e})")

    json.dump({"done": batch_start + BATCH_SIZE}, open(progress_file, "w", encoding="utf-8"))
    print(f"🧮 已完成 {min(batch_start + BATCH_SIZE, total)}/{total}")

with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(working))

if os.path.exists(progress_file):
    os.remove(progress_file)

elapsed = round(time.time() - start_time, 2)
print(f"✅ 检测完成，共 {len(working)//2} 条可用流，用时 {elapsed} 秒")
