import os
import csv
import time
import json
import subprocess
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean
from collections import defaultdict
from PIL import Image
import hashlib

# ==============================
# 配置区
# ==============================
CSV_FILE = "output/merge_total.csv"
OUTPUT_FILE = "output/working.csv"
LOG_DIR = "output/log"
TMP_FRAMES = "output/tmp_frames"

TIMEOUT = 15
BASE_THREADS = 50
MAX_THREADS = 150
BATCH_SIZE = 100
DEBUG = True

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36",
}

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(TMP_FRAMES, exist_ok=True)
SKIPPED_FILE = os.path.join(LOG_DIR, "skipped.log")
SUSPECT_FILE = os.path.join(LOG_DIR, "suspect.log")

# ==============================
# 工具函数
# ==============================
def log_skip(reason, title, url):
    with open(SKIPPED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{reason} -> {title}\n{url}\n")

def is_allowed(title, url):
    # 可扩展规则
    low_res_keywords = ["vga", "480p", "576p"]
    block_keywords = ["espanol"]
    text = f"{title} {url}".lower()
    if any(w in text for w in low_res_keywords + block_keywords):
        log_skip("FILTER", title, url)
        return False
    return True

def quick_check(url):
    start = time.time()
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        elapsed = round(time.time() - start, 2)
        ok = r.status_code < 400
        return ok, elapsed
    except Exception:
        return False, round(time.time()-start,2)

def ffprobe_check(url):
    start = time.time()
    try:
        cmd = [
            "ffprobe","-v","error",
            "-select_streams","v:0",
            "-show_entries","stream=codec_name",
            "-of","json", url
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        data = json.loads(proc.stdout or "{}")
        ok = "streams" in data and len(data["streams"])>0
    except Exception:
        ok = False
    elapsed = round(time.time()-start,2)
    return ok, elapsed

def hash_frame(frame_path):
    try:
        with Image.open(frame_path) as im:
            return hashlib.md5(im.tobytes()).hexdigest()
    except:
        return None

def static_video_check(url):
    tmp1 = os.path.join(TMP_FRAMES, "f1.jpg")
    tmp2 = os.path.join(TMP_FRAMES, "f2.jpg")
    try:
        # 截取第10秒和第11秒
        subprocess.run([
            "ffmpeg","-y","-i",url,
            "-vf","select='eq(n,250)'","-vframes","1",tmp1
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
        subprocess.run([
            "ffmpeg","-y","-i",url,
            "-vf","select='eq(n,275)'","-vframes","1",tmp2
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25)
        h1 = hash_frame(tmp1)
        h2 = hash_frame(tmp2)
        return h1 != h2
    except:
        return False
    finally:
        for f in [tmp1,tmp2]:
            if os.path.exists(f):
                os.remove(f)

def test_stream(title,url):
    url = url.strip()
    try:
        if not is_allowed(title,url):
            return None
        ok, _ = quick_check(url)
        if not ok:
            ok,_ = ffprobe_check(url)
        if not ok:
            log_skip("FAILED_CHECK", title, url)
            return None
        # 静态视频检测
        if not static_video_check(url):
            log_skip("STATIC_VIDEO", title, url)
            return None
        return [title,url]
    except Exception as e:
        log_skip("EXCEPTION", title, url)
        if DEBUG: print(f"❌ {title} -> {url} | {e}")
        return None

# ==============================
# 主逻辑
# ==============================
if __name__=="__main__":
    pairs = []
    with open(CSV_FILE,encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pairs.append((row["tvg-name"].strip(), row["URL"].strip()))
    total = len(pairs)

    all_working = []
    threads = min(MAX_THREADS, total)
    for batch_start in range(0,total,BATCH_SIZE):
        batch = pairs[batch_start:batch_start+BATCH_SIZE]
        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(test_stream,title,url):(title,url) for title,url in batch}
            for future in as_completed(futures):
                res = future.result()
                if res:
                    all_working.append(res)
        print(f"🧮 本批完成：{len(batch)} 条")

    # 写 CSV
    with open(OUTPUT_FILE,"w",newline="",encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["tvg-name","URL"])
        writer.writerows(all_working)
    print(f"✅ 可用源检测完成，共 {len(all_working)} 条，输出: {OUTPUT_FILE}")