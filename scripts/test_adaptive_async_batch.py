import argparse
import csv
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from statistics import mean

# ==============================
# 命令行参数
# ==============================
parser = argparse.ArgumentParser()
parser.add_argument("--csv", default="output/merge_total.csv", help="输入 CSV 文件，默认 merge_total.csv")
parser.add_argument("--m3u", default="output/working.m3u", help="输出 M3U 文件")
args = parser.parse_args()

CSV_FILE = args.csv
OUTPUT_FILE = args.m3u

# ==============================
# 配置
# ==============================
TIMEOUT = 10
MAX_THREADS = 50
skipped_file = "output/log/skipped.log"
os.makedirs(os.path.dirname(skipped_file), exist_ok=True)

# ==============================
# 读取 CSV
# ==============================
if not os.path.exists(CSV_FILE):
    print(f"❌ 输入 CSV 不存在: {CSV_FILE}")
    exit(1)

channels = []
with open(CSV_FILE, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        channels.append({
            "name": row["tvg-name"],
            "url": row["URL"],
            "group": row.get("地区", ""),
            "source": row.get("来源", "")
        })

print(f"📄 读取 CSV {CSV_FILE}，共 {len(channels)} 条频道")

# ==============================
# 检测函数
# ==============================
def check_stream(channel):
    url = channel["url"]
    try:
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200:
            return channel
        else:
            with open(skipped_file, "a", encoding="utf-8") as f:
                f.write(f"{channel['name']},{url},状态码:{r.status_code}\n")
            return None
    except Exception as e:
        with open(skipped_file, "a", encoding="utf-8") as f:
            f.write(f"{channel['name']},{url},异常:{e}\n")
        return None

# ==============================
# 批量检测
# ==============================
working_channels = []
with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    future_to_channel = {executor.submit(check_stream, ch): ch for ch in channels}
    for future in as_completed(future_to_channel):
        result = future.result()
        if result:
            working_channels.append(result)

# ==============================
# 输出 M3U
# ==============================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for ch in working_channels:
        extinf = f'#EXTINF:-1 tvg-name="{ch["name"]}" group-title="{ch["group"]}",{ch["name"]}'
        f.write(f"{extinf}\n{ch['url']}\n")

print(f"✅ 检测完成，可用频道 {len(working_channels)} 条，输出 M3U: {OUTPUT_FILE}")
print(f"⚠️ 失败或跳过源已记录在 {skipped_file}")