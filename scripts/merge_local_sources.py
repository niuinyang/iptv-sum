import os
import csv
import re

# ==============================
# 配置区
# ==============================
INPUT_DIR = "input/network/network_sources"
OUTPUT_M3U = "output/merge_total.m3u"
OUTPUT_CSV = "output/merge_total.csv"
MIDDLE_DIR = "output/middle"
LOG_DIR = "output/log"
os.makedirs("output", exist_ok=True)
os.makedirs(MIDDLE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ==============================
# 合并函数
# ==============================
def merge_m3u_files(input_dir):
    urls_seen = set()
    merged_channels = []

    skipped_log = []

    for filename in os.listdir(input_dir):
        if not filename.endswith(".m3u"):
            continue
        path = os.path.join(input_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("#EXTINF:"):
                info_line = line
                url_line = lines[i + 1] if i + 1 < len(lines) else ""
                if not url_line.startswith("http"):
                    skipped_log.append(f"⚠️ 无效 URL: {url_line} (文件: {filename})")
                    i += 2
                    continue
                if url_line in urls_seen:
                    i += 2
                    continue

                # 提取 tvg-name
                match_name = re.search(r'tvg-name="([^"]+)"', info_line)
                tvg_name = match_name.group(1) if match_name else ""

                merged_channels.append({
                    "tvg-name": tvg_name,
                    "info": info_line,
                    "url": url_line
                })
                urls_seen.add(url_line)
                i += 2
            else:
                i += 1

    return merged_channels, skipped_log


# ==============================
# 写入 M3U & CSV
# ==============================
def write_outputs(channels, m3u_path, csv_path, skipped_log):
    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in channels:
            f.write(f"{ch['info']}\n{ch['url']}\n")

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["tvg-name", "URL"])
        for ch in channels:
            writer.writerow([ch["tvg-name"], ch["url"]])

    # 保存跳过日志
    log_file = os.path.join(LOG_DIR, "skipped.log")
    with open(log_file, "w", encoding="utf-8") as f:
        for line in skipped_log:
            f.write(line + "\n")


# ==============================
# 主程序
# ==============================
if __name__ == "__main__":
    merged_channels, skipped_log = merge_m3u_files(INPUT_DIR)
    write_outputs(merged_channels, OUTPUT_M3U, OUTPUT_CSV, skipped_log)
    print(f"✅ 合并完成：共 {len(merged_channels)} 条频道")
    print(f"📁 输出 M3U: {OUTPUT_M3U}")
    print(f"📁 输出 CSV: {OUTPUT_CSV}")
    print(f"📁 跳过日志: {os.path.join(LOG_DIR, 'skipped.log')}")