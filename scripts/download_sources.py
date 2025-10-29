import requests
import os
import time
from pathlib import Path

# 下载源列表
URLS = {
    "taiwan": "https://freetv.fun/test_channels_taiwan_new.m3u",
    "united_states": "https://freetv.fun/test_channels_united_states_new.m3u",
    "macau": "https://freetv.fun/test_channels_macau_new.m3u",
    "hong_kong": "https://freetv.fun/test_channels_hong_kong_new.m3u",
    "singapore": "https://freetv.fun/test_channels_singapore_new.m3u",
}

# 本地保存路径
SAVE_DIR = Path("input/sources")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

def download_with_retry(name, url, retries=3):
    file_path = SAVE_DIR / f"{name}.m3u"
    for attempt in range(1, retries + 1):
        try:
            print(f"📡 正在下载 [{name}] ({attempt}/{retries}) → {url}")
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()

            text = resp.text.strip()
            if not text.startswith("#EXTM3U"):
                raise ValueError("内容不是有效的 M3U 文件")

            file_path.write_text(text, encoding="utf-8")
            print(f"✅ 成功保存 {file_path} （{len(text.splitlines())} 行）")
            return True

        except Exception as e:
            print(f"⚠️ 下载失败 [{name}]：{e}")
            time.sleep(2)

    print(f"❌ 多次重试后失败 [{name}]")
    return False


if __name__ == "__main__":
    print("🚀 开始下载 M3U 源...")
    for name, url in URLS.items():
        download_with_retry(name, url)
    print("\n✅ 所有源下载完成！")