import os
import csv
import requests
from pathlib import Path

# ==============================
# 路径配置（已更新）
# ==============================
INPUT_DIR = Path("input/network/network_sources")
OUTPUT_DIR = Path("output")
LOG_DIR = OUTPUT_DIR / "log"
MIDDLE_DIR = OUTPUT_DIR / "middle"

for p in [OUTPUT_DIR, LOG_DIR, MIDDLE_DIR]:
    p.mkdir(parents=True, exist_ok=True)

MERGE_M3U = OUTPUT_DIR / "merge_total.m3u"
MERGE_CSV = OUTPUT_DIR / "total.csv"

# ==============================
# 模拟浏览器请求头
# ==============================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# ==============================
# 函数：加载 M3U 文件（本地）
# ==============================
def load_local_m3u(path: Path):
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text.startswith("#EXTM3U"):
            raise ValueError("不是合法的 M3U 文件")
        return text.splitlines()
    except Exception as e:
        print(f"⚠️ 读取 {path.name} 失败: {e}")
        return []

# ==============================
# 主函数：合并所有源
# ==============================
def merge_sources():
    merged_entries = []
    seen_urls = set()
    total_sources = 0
    failed_sources = 0

    for file in INPUT_DIR.glob("*.m3u"):
        print(f"📡 读取源文件: {file.name}")
        lines = load_local_m3u(file)

        if not lines:
            print(f"⚠️ 源文件为空或无效: {file.name}")
            failed_sources += 1
            continue

        total_sources += 1
        current_info = None

        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                current_info = line
            elif line.startswith("http"):
                url = line
                if url not in seen_urls:
                    merged_entries.append((current_info, url))
                    seen_urls.add(url)

    # 输出结果
    if not merged_entries:
        print("⚠️ 没有合并到任何频道！")
    else:
        with open(MERGE_M3U, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for info, url in merged_entries:
                f.write(f"{info}\n{url}\n")

        with open(MERGE_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["#EXTINF", "URL"])
            for info, url in merged_entries:
                writer.writerow([info, url])

        print(f"✅ 合并完成：成功 {total_sources} 源，失败 {failed_sources} 源，"
              f"去重后 {len(merged_entries)} 条频道 → {MERGE_M3U} / {MERGE_CSV}")
        print(f"📁 中间文件 → {MIDDLE_DIR}")
        print(f"📁 日志文件 → {LOG_DIR}/skipped.log")


# ==============================
# 主程序入口
# ==============================
if __name__ == "__main__":
    merge_sources()