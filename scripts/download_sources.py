import aiohttp
import asyncio
import os
from aiohttp import ClientSession, ClientTimeout
from datetime import datetime
import random

# ==============================
# 配置区
# ==============================
SOURCE_LIST_FILE = "input/network/networksource.txt"  # 包含所有源的列表
SAVE_DIR = "input/network/network_sources"            # 下载保存路径
MAX_CONCURRENT = 5                                    # 并发下载数
RETRY_COUNT = 3                                       # 重试次数

# 模拟浏览器请求头
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/120.0",
]

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ==============================
# 创建文件夹
# ==============================
os.makedirs(SAVE_DIR, exist_ok=True)


# ==============================
# 异步下载函数
# ==============================
async def fetch(session: ClientSession, url: str, retries=RETRY_COUNT):
    for attempt in range(1, retries + 1):
        try:
            headers = HEADERS.copy()
            headers["User-Agent"] = random.choice(USER_AGENTS)

            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    return text
                else:
                    print(f"⚠️ [{resp.status}] {url}")
        except Exception as e:
            print(f"⚠️ 第 {attempt}/{retries} 次重试失败：{url} ({e})")
            await asyncio.sleep(2 * attempt)
    return None


# ==============================
# 下载任务
# ==============================
async def download_all():
    # 读取源列表
    if not os.path.exists(SOURCE_LIST_FILE):
        print(f"❌ 未找到源列表文件: {SOURCE_LIST_FILE}")
        return

    with open(SOURCE_LIST_FILE, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print("❌ 源列表为空，退出。")
        return

    print(f"📡 共 {len(urls)} 个源，将保存到 {SAVE_DIR}")

    timeout = ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit_per_host=MAX_CONCURRENT)
    async with ClientSession(timeout=timeout, connector=connector) as session:
        tasks = []
        for url in urls:
            tasks.append(download_one(session, url))
        await asyncio.gather(*tasks)


# ==============================
# 下载单个源
# ==============================
async def download_one(session, url):
    filename = os.path.basename(url.split("?")[0])
    if not filename.endswith(".m3u"):
        filename += ".m3u"

    save_path = os.path.join(SAVE_DIR, filename)
    print(f"⬇️ 正在下载: {url}")

    content = await fetch(session, url)
    if content:
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 保存成功: {save_path} ({len(content)} 字节)")
    else:
        print(f"❌ 下载失败: {url}")


# ==============================
# 主入口
# ==============================
if __name__ == "__main__":
    print(f"🚀 IPTV 源下载开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    asyncio.run(download_all())
    print(f"🏁 IPTV 源下载完成: {SAVE_DIR}")