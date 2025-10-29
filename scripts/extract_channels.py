import csv
import re
import unicodedata
from opencc import OpenCC
import os
import difflib

# ==============================
# 配置区
# ==============================
M3U_FILE = "output/working.m3u"
OUTPUT_DIR = os.path.join("output", "sum_cvs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 地区与对应 find CSV 文件及来源标识
REGIONS = {
    "国际": {"csv": "input/network/find_intl.csv", "source": "国际源", "out": "find_international_sum.csv"},
    "台湾": {"csv": "input/network/find_tw.csv", "source": "台湾源", "out": "find_taiwan_sum.csv"},
    "香港": {"csv": "input/network/find_hk.csv", "source": "香港源", "out": "find_hk_sum.csv"},
    "澳门": {"csv": "input/network/find_mo.csv", "source": "澳门源", "out": "find_mo_sum.csv"}
}

# 简繁转换器（繁体 -> 简体）
cc = OpenCC('t2s')

# ==============================
# 文本标准化函数
# ==============================
def normalize_text(text):
    if not text:
        return ""
    text = cc.convert(text)  # 繁转简
    text = unicodedata.normalize("NFKC", text)
    text = ''.join(
        c for c in text
        if not (c.isspace() or unicodedata.category(c).startswith(('P', 'S')))
    )
    return text.lower()

# ==============================
# 提取频道函数
# ==============================
def extract_channels(find_csv, region_name, source_label, output_file):
    # 读取搜索列表
    with open(find_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        search_names = [row[0].strip() for row in reader if row]

    search_norm = [normalize_text(name) for name in search_names]

    # 存储匹配结果
    matches_dict = {name: [] for name in search_names}
    seen_urls = set()  # 去重 URL

    # 读取 M3U 文件
    with open(M3U_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            info_line = line
            url_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if url_line in seen_urls or not url_line.startswith("http"):
                i += 2
                continue

            # 提取 tvg-name
            match_name = re.search(r'tvg-name="([^"]+)"', info_line)
            tvg_name_original = match_name.group(1) if match_name else ""
            tvg_norm = normalize_text(tvg_name_original)

            for idx, name_norm in enumerate(search_norm):
                matched = False

                # 1️⃣ 完全包含
                if name_norm in tvg_norm:
                    matched = True

                # 2️⃣ 正则匹配（防止特殊字符）
                if not matched:
                    pattern = re.escape(name_norm)
                    if re.search(pattern, tvg_norm):
                        matched = True

                # 3️⃣ 模糊匹配（相似度 > 80%）
                if not matched:
                    ratio = difflib.SequenceMatcher(None, name_norm, tvg_norm).ratio()
                    if ratio > 0.8:
                        matched = True

                if matched:
                    matches_dict[search_names[idx]].append([
                        search_names[idx],
                        region_name,
                        url_line,
                        source_label,
                        tvg_name_original
                    ])
                    seen_urls.add(url_line)
                    break
            i += 2
        else:
            i += 1

    # 写入 CSV
    output_path = os.path.join(OUTPUT_DIR, output_file)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["tvg-name", "地区", "URL", "来源", "原始tvg-name"])
        for name in search_names:
            writer.writerows(matches_dict[name])

    total_matches = sum(len(v) for v in matches_dict.values())
    print(f"✅ {region_name} 匹配完成，共 {total_matches} 个频道，输出: {output_path}")

# ==============================
# 执行所有地区提取
# ==============================
if __name__ == "__main__":
    for region, cfg in REGIONS.items():
        csv_file = cfg["csv"]
        source_label = cfg["source"]
        output_file = cfg["out"]
        if not os.path.exists(csv_file):
            print(f"⚠️ 找不到 {region} 的查找 CSV: {csv_file}, 已跳过")
            continue
        extract_channels(csv_file, region, source_label, output_file)