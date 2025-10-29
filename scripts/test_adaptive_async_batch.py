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
from PIL import Image
import hashlib
import shutil

# ==============================
# 文件夹结构
# ==============================
OUTPUT_DIR = "output"
LOG_DIR = os.path.join(OUTPUT_DIR, "log")
MIDDLE_DIR = os.path.join(OUTPUT_DIR, "middle")
TMP_FRAMES = os.path.join(MIDDLE_DIR, "frames")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(MIDDLE_DIR, exist_ok=True)
os.makedirs(TMP_FRAMES, exist_ok=True)

# ==============================
# 配置区
# ==============================
CSV_FILE = os.path.join(OUTPUT_DIR, "merge_total.csv")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "working.m3u")
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

# dxl 排除源
DXL_EXCLUDE_SOURCES = ["济南移动", "上海移动"]

# ==============================
# 工具函数
# ==============================
def log_skip(reason, title, url):
    with open(SKIPPED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{reason} -> {title}\n{url}\n")

def log_suspect(reason, url):
    with open(SUSPECT_FILE, "a", encoding="utf-8") as f:
        f.write(f"{reason} -> {url}\n")

def is_allowed(title, url, source=None, dxl_mode=False):
    text = f"{title} {url}".lower()
    if any(w in text for w in WHITELIST_PATTERNS):
        return True
    if any(kw in text for kw in LOW_RES_KEYWORDS):
        log_skip("LOW_RES", title, url)
        return False
    if any(kw in text for kw in BLOCK_KEYWORDS):
        log_skip("BLOCK_KEYWORD", title, url)
        return False
    if dxl_mode and source in DXL_EXCLUDE_SOURCES:
        log_skip("DXL_EXCLUDE", title, url)
        return False
    return True

def quick_check(url):
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

def hash_frame(image_path):
    try:
        with Image.open(image_path) as im:
            return hashlib.md5(im.tobytes()).hexdigest()
    except:
        return None

def detect_static_video(url):
    tmp_file1 = os.path.join(TMP_FRAMES, "frame1.jpg")
    tmp_file2 = os.path.join(TMP_FRAMES, "frame2.jpg")
    try:
        # 延迟截第10秒和11秒帧
        subprocess.run([
            "ffmpeg", "-y", "-i", url, "-vf", "select='eq(n,250)'", "-vframes", "1", tmp_file1
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        subprocess.run([
            "ffmpeg", "-y", "-i", url, "-vf", "select='eq(n,275)'", "-vframes", "1", tmp_file2
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        h1 = hash_frame(tmp_file1)
        h2 = hash_frame(tmp_file2)
        if h1 and h2 and h1 == h2:
            return True
    except:
        return False
    finally:
        for f in [tmp_file1, tmp_file2]:
            if os.path.exists(f):
                os.remove(f)
    return False

def test_stream(title, url, source=None, dxl_mode=False):
    url = url.strip()
    try:
        if not is_allowed(title, url, source, dxl_mode):
            return False, 0, url
        ok, elapsed, final_url = quick_check(url)
        if not ok:
            ok, elapsed, final_url = ffprobe_check(url)
        if ok and detect_static_video(final_url):
            log_skip("STATIC_VIDEO", title, final_url)
            ok = False
        return ok, elapsed, final_url
    except Exception as e:
        log_skip("EXCEPTION", title, url)
        if DEBUG:
            print(f"❌ EXCEPTION {title} -> {url} | {e}")
        return False, 0, url

def detect_optimal_threads():
    cpu_threads = multiprocessing.cpu_count()*5
    return min(MAX_THREADS, cpu_threads)

def extract_name(title):
    return title.split(",")[-1].strip() if "," in title else title.strip()

def write_m3u(working_list, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, url, elapsed in working_list:
            f.write(f'#EXTINF:-1 tvg-name="{title}" group-title="测试",{title}\n{url}\n')

# ==============================
# 主逻辑
# ==============================
if __name__ == "__main__":
    for log_file in [SKIPPED_FILE, SUSPECT_FILE]:
        if os.path.exists(log_file):
            os.remove(log_file)

    # 读取 CSV
    pairs = []
    with open(CSV_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        title_col = next((c for c in fieldnames if "name" in c.lower() or "title" in c.lower()), None)
        url_col = next((c for c in fieldnames if "url" in c.lower()), None)
        source_col = next((c for c in fieldnames if "source" in c.lower()), None)
        for row in reader:
            title = row[title_col].strip()
            url = row[url_col].strip()
            source = row[source_col].strip() if source_col else None
            pairs.append((title, url, source))

    total = len(pairs)
    threads = detect_optimal_threads()
    print(f"⚙️ 动态线程数：{threads}")
    all_working = []

    for batch_start in range(0, total, BATCH_SIZE):
        batch = pairs[batch_start:batch_start+BATCH_SIZE]
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(test_stream, title, url, source, dxl_mode=False):(title,url) for title,url,source in batch}
            for future in as_completed(futures):
                title, url = futures[future]
                ok, elapsed, final_url = future.result()
                if ok:
                    all_working.append((title, final_url, elapsed))
                    if DEBUG:
                        print(f"✅ {extract_name(title)} ({elapsed}s)")

    # 写入 M3U
    write_m3u(all_working, OUTPUT_FILE)
    print(f"✅ 检测完成，共 {len(all_working)} 条可用流，用时 {round(time.time()-start_time,1)} 秒")