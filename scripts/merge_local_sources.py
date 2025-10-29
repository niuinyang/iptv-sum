import os
from pathlib import Path

INPUT_DIR = Path("input/sources")
OUTPUT_FILE = Path("output/merge_total.m3u")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

def merge_local_sources():
    merged_lines = []
    seen = set()
    count_files = 0

    for file in INPUT_DIR.glob("*.m3u"):
        count_files += 1
        with file.open("r", encoding="utf-8") as f:
            lines = f.readlines()
            merged_lines.extend(lines)
            print(f"✅ 已加载 {file.name} 共 {len(lines)} 行")

    if count_files == 0:
        print("⚠️ 未找到任何 M3U 文件！请检查 input/sources/")
        return

    # 去重
    final_lines = []
    for line in merged_lines:
        if line.startswith("#EXTINF") or line.startswith("http"):
            if line not in seen:
                seen.add(line)
                final_lines.append(line)

    OUTPUT_FILE.write_text("#EXTM3U\n" + "".join(final_lines), encoding="utf-8")
    print(f"✅ 合并完成：{count_files} 个源 → {len(final_lines)} 条频道")
    print(f"📁 输出文件：{OUTPUT_FILE}")

if __name__ == "__main__":
    merge_local_sources()