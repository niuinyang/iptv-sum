#!/usr/bin/env python3
# download_m3u.py
# 用法: python download_m3u.py
# 读取 input/network/networksource.txt，保存到 input/network/network_sources/

import os
import sys
import re
import time
import random
import logging
from urllib.parse import urlparse, unquote
import requests

# 配置
SOURCE_LIST = "input/network/networksource.txt"
OUTPUT_DIR = "input/network/network_sources"
LOG_FILE = "download_m3u.log"
ERROR_LOG = "download_errors.log"

RETRIES = 3
BACKOFF_BASE = 2  # 指数退避基数
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
MIN_SIZE_BYTES = 200     # 最小字节数判定为有效文件（可根据需要调整）
M3U_KEYWORDS = ["#EXTM3U", ".m3u", ".m3u8"]

# 一组常见浏览器 UA，随机选择以伪装
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edg/117.0.0.0 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
    # Safari macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    # iPhone Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

# 日志设置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

def sanitize_filename(s: str) -> str:
    # 移除非法字符，限制长度
    s = unquote(s)
    s = re.sub(r"[:/?#\[\]@!$&'()*+,;=\"<>\\|]+", "_", s)
    s = re.sub(r"\s+", "_", s)
    return s[:200]

def guess_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = os.path.basename(parsed.path)
    if not name:
        name = parsed.netloc
    name = sanitize_filename(name)
    if not os.path.splitext(name)[1]:
        name = name + ".m3u"
    return name

def looks_like_m3u(content_bytes: bytes) -> bool:
    try:
        txt = content_bytes[:1024].decode("utf-8", errors="ignore").lower()
    except Exception:
        return False
    for kw in M3U_KEYWORDS:
        if kw.lower() in txt:
            return True
    return False

def download_url(url: str, out_path: str) -> (bool, str):
    # 返回 (成功/失败, message)
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": f"https://{urlparse(url).netloc}/",
        "Connection": "keep-alive",
    }

    temp_path = out_path + ".tmp"
    for attempt in range(1, RETRIES+1):
        try:
            logging.info(f"Downloading ({attempt}/{RETRIES}): {url}")
            with requests.get(url, headers=headers, stream=True,
                              timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), allow_redirects=True) as r:
                status = r.status_code
                if status != 200:
                    msg = f"HTTP {status}"
                    logging.warning(msg)
                    raise Exception(msg)
                # write to temp file
                with open(temp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                # 校验
                size = os.path.getsize(temp_path)
                if size < MIN_SIZE_BYTES:
                    msg = f"File too small ({size} bytes)"
                    raise Exception(msg)
                with open(temp_path, "rb") as f:
                    head = f.read(2048)
                if not looks_like_m3u(head):
                    # 依然可以保存，但标记为可疑
                    msg = "Content does not look like M3U"
                    logging.warning(msg)
                    # 仍然将文件移动并返回成功（如需强校验可改为失败）
                    os.replace(temp_path, out_path)
                    return True, "Downloaded but content not obviously M3U"
                # 一切正常
                os.replace(temp_path, out_path)
                return True, "OK"
        except Exception as e:
            wait = BACKOFF_BASE ** (attempt - 1)
            logging.warning(f"Attempt {attempt} failed for {url}: {e}. Backing off {wait}s")
            time.sleep(wait + random.random())
    # all retries failed
    # 清理临时文件
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except:
            pass
    return False, f"Failed after {RETRIES} attempts"

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)

def main():
    ensure_dirs()
    if not os.path.exists(SOURCE_LIST):
        logging.error(f"Source list not found: {SOURCE_LIST}")
        sys.exit(2)

    failed = []
    total = 0
    with open(SOURCE_LIST, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        url = line.split()[0]  # 支持后面跟注释
        total += 1
        try:
            fname = guess_filename_from_url(url)
            out_path = os.path.join(OUTPUT_DIR, fname)
            # 如果已有文件且文件大小看起来正常，则跳过（可修改为总是覆盖）
            if os.path.exists(out_path) and os.path.getsize(out_path) > MIN_SIZE_BYTES:
                logging.info(f"Already exists, skip: {out_path}")
                continue
            success, msg = download_url(url, out_path)
            if success:
                logging.info(f"Saved: {out_path} ({msg})")
            else:
                logging.error(f"Failed: {url} -> {msg}")
                failed.append((url, msg))
        except Exception as e:
            logging.exception(f"Unhandled error for {url}: {e}")
            failed.append((url, str(e)))

    # 写失败日志
    if failed:
        with open(ERROR_LOG, "a", encoding="utf-8") as ef:
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            ef.write(f"\n# {ts} - failed {len(failed)}/{total}\n")
            for u, m in failed:
                ef.write(f"{u}    # {m}\n")
    logging.info(f"Done. Total URLs processed: {total}. Failed: {len(failed)}.")

if __name__ == "__main__":
    main()