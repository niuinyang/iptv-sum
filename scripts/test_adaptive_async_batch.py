import csv
import os
import asyncio
import aiohttp
from aiohttp import ClientTimeout
from concurrent.futures import ThreadPoolExecutor
from statistics import mean

# ==============================
# 配置区
# ==============================
CSV_FILE = "output/merge_total.csv"   # 使用 merge_total.csv
OUTPUT_M3U = "output/working.m3u"
TIMEOUT = 10
BATCH_SIZE = 200
MAX_THREADS = 50

os.makedirs(os.path.dirname(OUTPUT_M3U), exist_ok=True)

# ==============================
# 读取 CSV
# ==============================
channels = []
with open(CSV_FILE, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    if "tvg-name" not in reader.fieldnames or "URL" not in reader.fieldnames:
        raise ValueError(f"CSV 列名不正确: {reader.fieldnames}")
    for row in reader:
        if not row or not row.get("tvg-name") or not row.get("URL"):
            continue
        channels.append({
            "name": row["tvg-name"],
            "url": row["URL"]
        })

print(f"✅ 读取 CSV 完成，共 {len(channels)} 条有效频道")

# ==============================
# 异步检测函数
# ==============================
async def check_stream(session, channel):
    url = channel["url"]
    try:
        async with session.head(url, timeout=ClientTimeout(total=TIMEOUT)) as resp:
            if resp.status == 200:
                return channel
    except Exception:
        return None
    return None

async def run_checks(channels):
    results = []
    connector = aiohttp.TCPConnector(limit_per_host=MAX_THREADS)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_stream(session, ch) for ch in channels]
        for i in range(0, len(tasks), BATCH_SIZE):
            batch = tasks[i:i+BATCH_SIZE]
            batch_results = await asyncio.gather(*batch)
            results.extend([r for r in batch_results if r])
            print(f"⏱ 检测进度: {min(i+BATCH_SIZE, len(tasks))}/{len(tasks)}")
    return results

# ==============================
# 生成 M3U
# ==============================
def write_m3u(channels, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in channels:
            f.write(f'#EXTINF:-1,{ch["name"]}\n{ch["url"]}\n')
    print(f"✅ 已生成 {output_file}，共 {len(channels)} 条可用频道")

# ==============================
# 主程序
# ==============================
def main():
    loop = asyncio.get_event_loop()
    valid_channels = loop.run_until_complete(run_checks(channels))
    write_m3u(valid_channels, OUTPUT_M3U)
    print("✅ 检测完成！")

if __name__ == "__main__":
    main()