import os
import re
import json
import time
import subprocess
import requests
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

LOW_RES_KEYWORDS = ["vga", "480p", "576p"]
BLOCK_KEYWORDS = ["espanol"]
WHITELIST_PATTERNS = [".ctv", ".sdserver", ".sdn.", ".sda.", ".sdstream", "sdhd", "hdsd"]

# ==============================
# 工具函数
# ==============================
def log_skip(reason, title, url):
    with open(skipped_file, "a", encoding="utf-8") as f:
        f.write(f"{reason} -> {title}\n{url}\n")

def log_suspect(reason, url):
    with open(suspect_file, "a", encoding="utf-8") as f:
        f.write(f"{reason} -> {url}\n")

def is_allowed(title, url):
    text = f"{title} {url}".lower()
    # 白名单防误杀
    if any(w in text for w in WHITELIST_PATTERNS):
        return True
    # 跳过低清
    if any(re.search(r'([_\-\s\.\(\[]'+kw+'[\s\)\]\._-])', text) for kw in LOW_RES_KEYWORDS):
        log_skip("LOW_RES", title, url)
        return False
    # 屏蔽关键词
    for kw in BLOCK_KEYWORDS:
        if re.search(rf'\b{kw}\b', text):
            log_skip("BLOCK_KEYWORD", title, url)
            return False
    return True

def quick_check(url):
    """HEAD 快速检测"""
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        ctype = r.headers.get("content-type","").lower()
        if r.status_code < 400 and any(v in ctype for v in ["video/","mpegurl","x-mpegurl","application/vnd.apple.mpegurl","application/x-mpegurl","application/octet-stream"]):
            return True, r.url
    except:
        pass
    return False, url

def ffprobe_check(url):
    """使用 ffprobe 检测视频流"""
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
    except:
        ok = False
    elapsed = round(time.time()-start,3)
    return ok, elapsed, url

def test_stream(url):
    """检测流可用性"""
    ok, final_url = quick_check(url)
    if not ok:
        ok, elapsed, final_url = ffprobe_check(url)
    else:
        elapsed = round(TIMEOUT/2,3)  # 快速检查用默认耗时
    return ok, elapsed, final_url

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
lines = open(input_file, encoding="utf-8").read().splitlines()
pairs = []
i=0
while i < len(lines):
    if lines[i].startswith("#EXTINF") and i+1<len(lines):
        title, url = lines[i], lines[i+1]
        if is_allowed(title, url):
            pairs.append((title, url))
        else:
            print(f"🚫 跳过: {title}")
        i+=2
    else:
        i+=1

# 恢复进度
done_index = 0
if os.path.exists(progress_file):
    try:
        done_index = json.load(open(progress_file,encoding="utf-8")).get("done",0)
        print(f"🔄 恢复进度，从第 {done_index} 条继续")
    except:
        pass

total = len(pairs)
threads = detect_optimal_threads()
print(f"⚙️ 动态并发线程数：{threads}")
print(f"🚀 开始检测 {total} 条流，每批 {BATCH_SIZE} 条")

start_time = time.time()
all_working = []

for batch_start in range(done_index, total, BATCH_SIZE):
    batch = pairs[batch_start:batch_start+BATCH_SIZE]
    working_batch = []
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(test_stream,url):(title,url) for title,url in batch}
        for future in as_completed(futures):
            title,url = futures[future]
            try:
                ok, elapsed, final_url = future.result()
                if ok:
                    working_batch.append((title, final_url, elapsed))
                    print(f"✅ {extract_name(title)} ({elapsed}s)")
                else:
                    log_skip("FAILED_CHECK", title, url)
            except Exception as e:
                log_skip("EXCEPTION", title, url)
    all_working.extend(working_batch)
    json.dump({"done":min(batch_start+BATCH_SIZE,total)}, open(progress_file,"w",encoding="utf-8"))
    print(f"🧮 本批完成：{len(working_batch)}/{len(batch)} 可用流 | 已完成 {min(batch_start+BATCH_SIZE,total)}/{total}")

if os.path.exists(progress_file):
    os.remove(progress_file)

# ==============================
# 分组、排序、去重
# ==============================
grouped = defaultdict(list)
for title,url,elapsed in all_working:
    name = extract_name(title).lower()
    grouped[name].append((title,url,elapsed))

with open(output_file,"w",encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for name in sorted(grouped.keys()):
        group_sorted = sorted(grouped[name], key=lambda x:x[2])
        for title,url,_ in group_sorted:
            f.write(f"{title}\n{url}\n")

elapsed_total = round(time.time()-start_time,2)
print(f"\n✅ 检测完成，共 {len(all_working)} 条可用高清流，用时 {elapsed_total} 秒")
print(f"📁 可用源: {output_file}")
print(f"⚠️ 失败或过滤源: {skipped_file}")
print(f"🕵️ 可疑误杀源: {suspect_file}")