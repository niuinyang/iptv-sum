import aiohttp
import asyncio
import os
import time
import requests
from aiohttp import ClientTimeout

# ==============================
# 配置区
# ==============================
SOURCE_LIST = [
    "https://freetv.fun/test_channels_taiwan_new.m3u",
    "https://freetv.fun/test_channels_hong_kong_new.m3u",
    "https://freetv.fun/test_channels_macau_new.m3u",
    "https://freetv.fun/test_channels_singapore_new.m3u",
    "https://freetv.fun/test_channels_united_states_new.m3u"
]

OUTPUT_DIR = "input/network/network_sources"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Connection": "keep-alive",
}

MAX_RETRIES = 3
TIMEOUT = 15


# ==============================
# 异步下载函数
# ==============================
async def fetch(session, url):
    filename = os.path.join(OUTPUT_DIR, os.path.basename(url))
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with session.get(url, timeout=ClientTimeout(total=TIMEOUT)) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(content)
                    print(f"✅ 下载成功: {url} → {filename}")
                    return
                else:
                    print(f"⚠️ [{resp.status}] 无法下载: {url} (尝试 {attempt}/{MAX_RETRIES})")
        except Exception as e:
            print(f"⚠️ 下载失败 ({attempt}/{MAX_RETRIES}): {url} -> {e}")
        await asyncio.sleep(2)

    # Fallback to requests
    print(f"🔁 尝试 fallback 同步下载: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 200:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"✅ fallback 成功: {url}")
        else:
            print(f"❌ fallback 失败: {url} ({resp.status_code})")
    except Exception as e:
        print(f"❌ fallback 异常: {url} -> {e}")


# ==============================
# 主函数
# ==============================
async def main():
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tasks = [fetch(session, url) for url in SOURCE_LIST]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    start_time = time.time()
    print("📡 开始下载 M3U 源文件...\n")
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ 异步主任务出错: {e}")

    print(f"\n✅ 全部下载任务完成，用时 {time.time() - start_time:.1f} 秒。")