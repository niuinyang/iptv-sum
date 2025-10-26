import os
import csv
import time
import json
import subprocess
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from statistics import mean
import multiprocessing

# ==============================
# 文件夹结构
# ==============================
OUTPUT_DIR = "output"
LOG_DIR = os.path.join(OUTPUT_DIR, "log")
MIDDLE_DIR = os.path.join(OUTPUT_DIR, "middle")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(MIDDLE_DIR, exist_ok=True)

# ==============================
# 配置区
# ==============================
CSV_FILE = os.path.join(OUTPUT_DIR, "total.csv")        # 输入 CSV
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "working.m3u")  # 可用流输出
PROGRESS_FILE = os.path.join(MIDDLE_DIR, "progress.json")
SKIPPED_FILE = os.path.join(LOG_DIR, "skipped.log")
SUSPECT_FILE = os.path.join(LOG_DIR, "suspect.log")

TIMEOUT = 15
BASE_THREADS = 50
MAX_THREADS = 200
BATCH_SIZE = 200
DEBUG = True

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
}

LOW_RES_KEYWORDS = ["vga", "480p", "576p"]
BLOCK_KEYWORDS = ["espanol"]
WHITELIST_PATTERNS = [".ctv", ".sdserver", ".sdn.", ".sda.", ".sdstream", "sdhd", "hdsd"]

# ==============================
# 工具函数
# ==============================
def log_skip(reason, title, url):
    with open(SKIPPED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{reason} -> {title}\n{url}\n")

def log_suspect(reason, url):
    with open(SUSPECT_FILE, "a", encoding="utf-8") as f:
        f.write(f"{reason} -> {url}\n")

def is_allowed(title, url):
    text = f"{title} {url}".lower()
    # 白名单防误杀
    if any(w in text for w in WHITELIST_PATTERNS):
        return True
    # 跳过低清
    if any(kw in text for kw in LOW_RES_KEYWORDS):
        log_skip("LOW_RES", title, url)
        return False
    # 屏蔽关键词
    if any(kw in text for kw in BLOCK_KEYWORDS):
        log_skip("BLOCK_KEYWORD", title, url)
        return False
    return True

def quick_check(url):
    """HEAD 快速检测"""
    start = time.time()
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        elapsed = round(time.time() - start, 3)
        ctype = r.headers.get("content-type", "").lower()
        ok = r.status_code < 400 and any(v in ctype for v in [
            "video/", "mpegurl", "x-mpegurl",
            "application/vnd.apple.mpegurl",
            "application/x-mpegurl",
            "application/octet-stream"
        ])
        return ok, elapsed, r.url
    except Exception:
        return False, round(time.time() - start, 3), url

def ffprobe_check(url):
    """ffprobe 检测视频流"""
    start = time.time()
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name",
            "-of", "json", url
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        data = json.loads(proc.stdout or "{}")
        ok = "streams" in data and len(data["streams"]) > 0
    except Exception:
        ok = False
    elapsed = round(time.time() - start, 3)
    return ok, elapsed, url

def test_stream(title, url):
    """
    检测流可用性
    白名单也做 HEAD/ffprobe
    """
    url = url.strip()
    try:
        ok, elapsed, final_url = quick_check(url)
        if not ok:
            ok, elapsed, final_url = ffprobe_check(url)
        return ok, elapsed, final_url
    except Exception as e:
        log_skip("EXCEPTION", title, url)
        if DEBUG:
            print(f"❌ EXCEPTION {title} -> {url} | {e}")
        return False, 0, url

def detect_optimal_threads():
    """动态线程数"""
    test_urls = ["https://www.apple.com","https://www.google.com","https://www.microsoft.com"]
    times = []
    for u in test_urls:
        t0 = time.time()
        try:
            requests.head(u, timeout=TIMEOUT)
        except:
            pass
        times.append(time.time()-t0)
    avg = mean(times)
    cpu_threads = multiprocessing.cpu_count()*5
    if avg<0.5:
        return min(MAX_THREADS, cpu_threads)
    elif avg<1:
        return min(150, cpu_threads)
    elif avg<2:
        return min(100, cpu_threads)
    else:
        return BASE_THREADS

def extract_name(title):
    if "," in title:
        return title.split(",")[-1].strip()
    return title.strip()

# ==============================
# 主逻辑
# ==============================
if __name__ == "__main__":
    # 清空日志
    for log_file in [SKIPPED_FILE, SUSPECT_FILE]:
        if os.path.exists(log_file):
            os.remove(log_file)

    # 1. 导入 CSV
    pairs = []
    with open(CSV_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row["title"].strip()
            url = row["url"].strip()
            pairs.append((title, url))

    # 2. 过滤
    filtered_pairs = [(t,u) for t,u in pairs if is_allowed(t,u)]
    print(f"🚫 跳过源: {len(pairs)-len(filtered_pairs)} 条")

    total = len(filtered_pairs)
    threads = detect_optimal_threads()
    print(f"⚙️ 动态线程数：{threads}")
    print(f"🚀 开始检测 {total} 条流，每批 {BATCH_SIZE} 条")

    # 3. 批量检测
    all_working = []
    start_time = time.time()
    done_index = 0

    if os.path.exists(PROGRESS_FILE):
        try:
            done_index = json.load(open(PROGRESS_FILE,encoding="utf-8")).get("done",0)
            print(f"🔄 恢复进度，从第 {done_index} 条继续")
        except:
            pass

    for batch_start in range(done_index, total, BATCH_SIZE):
        batch = filtered_pairs[batch_start:batch_start+BATCH_SIZE]
        working_batch = []
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(test_stream,title,url):(title,url) for title,url in batch}
            for future in as_completed(futures):
                title,url = futures[future]
                try:
                    ok, elapsed, final_url = future.result()
                    if ok:
                        working_batch.append((title, final_url, elapsed))
                        if DEBUG:
                            print(f"✅ {extract_name(title)} ({elapsed}s)")
                    else:
                        log_skip("FAILED_CHECK", title, url)
                except Exception as e:
                    log_skip("EXCEPTION", title, url)
        all_working.extend(working_batch)
        json.dump({"done":min(batch_start+BATCH_SIZE,total)}, open(PROGRESS_FILE,"w",encoding="utf-8"))
        print(f"🧮 本批完成：{len(working_batch)}/{len(batch)} 可用流 | 已完成 {min(batch_start+BATCH_SIZE,total)}/{total}")

    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    # 4. 分组、按耗时排序
    grouped = defaultdict(list)
    for title,url,elapsed in all_working:
        name = extract_name(title).lower()
        grouped[name].append((title,url,elapsed))

    with open(OUTPUT_FILE,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name in sorted(grouped.keys()):
            group_sorted = sorted(grouped[name], key=lambda x: x[2])
            for title,url,_ in group_sorted:
                f.write(f"{title}\n{url}\n")

    elapsed_total = round(time.time()-start_time,2)
    print(f"\n✅ 检测完成，共 {len(all_working)} 条可用流，用时 {elapsed_total} 秒")
    print(f"📁 可用源: {OUTPUT_FILE}")
    print(f"⚠️ 失败或过滤源: {SKIPPED_FILE}")
    print(f"🕵️ 可疑误杀源: {SUSPECT_FILE}")
