import aiohttp
import asyncio
import os
import time
import random
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

# 可选代理备用前缀（通过 jsDelivr 或 Cloudflare Worker 代理 freetv.fun）
PROXY_PREFIXES = [
    "https://cdn.jsdelivr.net/gh/freetvsource/proxy@main/?url=",
    "https://workers.cloudflare.com/?url="
]

OUTPUT_DIR = "input/network/network_sources"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 多个 UA 随机使用，模拟不同客户端
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Android 13; Mobile) AppleWebKit/537.36 Chrome/128.0.6613.138 Mobile Safari/537.36"
]

MAX_RETRIES = 3
TIMEOUT = 20


# ==============================
# 异步下载函数
# ==============================
async def fetch(session, url):
    filename = os.path.join(OUTPUT_DIR, os.path.basename(url))
    headers = {"User-Agent": random.choice(USER_AGENTS), "Referer": "https://freetv.fun/"}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            await asyncio.sleep(random.uniform(1.5, 3.5))  # 随机延迟防封
            async with session.get(url, timeout=ClientTimeout(total=TIMEOUT)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(text)
                    print(f"✅ 下载成功: {url} → {filename}")
                    return
                else:
                    print(f"⚠️ [{resp.status}] 无法下载: {url} (尝试 {attempt}/{MAX_RETRIES})")
        except Exception as e:
            print(f"⚠️ 异步错误 ({attempt}/{MAX_RETRIES}): {url} -> {e}")
        await asyncio.sleep(2)

    # 尝试代理下载
    for proxy_prefix in PROXY_PREFIXES:
        proxy_url = proxy_prefix + url
        print(f"🔁 尝试代理下载: {proxy_url}")
        try:
            resp = requests.get(proxy_url, headers=headers, timeout=TIMEOUT)
            if resp.status_code == 200 and "#EXTM3U" in resp.text:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(resp.text)
                print(f"✅ 代理下载成功: {proxy_url}")
                return
            else:
                print(f"❌ 代理失败 ({resp.status_code}): {proxy_url}")
        except Exception as e:
            print(f"❌ 代理异常: {proxy_url} -> {e}")

    print(f"❌ 最终下载失败: {url}")


# ==============================
# 主任务
# ==============================
async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in SOURCE_LIST]
        await asyncio.gather(*tasks)


# ==============================
# 主入口
# ==============================
if __name__ == "__main__":
    start_time = time.time()
    print("📡 开始下载 M3U 源文件...\n")

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ 主任务异常: {e}")

    print(f"\n✅ 全部下载任务完成，用时 {time.time() - start_time:.1f} 秒。")
