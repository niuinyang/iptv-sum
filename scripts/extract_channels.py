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
OUTPUT_DIR = "output/sum_cvs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 各地区对应查找文件、输出文件与来源标识
REGIONS = {
    "国际": {
        "find": "input/network/find/find_international.csv",
        "out": "find_international_sum.csv",
        "source": "国际源",
    },
    "台湾": {
        "find": "input/network/find/find_taiwan.csv",
        "out": "find_taiwan_sum.csv",
        "source": "台湾源",
    },
    "香港": {
        "find": "input/network/find/find_hk.csv",
        "out": "find_hk_sum.csv",
        "source": "香港源",
    },
    "澳门": {
        "find": "input/network/find/find_mo.csv",
        "out": "find_mo_sum.csv",
        "source": "澳门源",
    },
}

# 简繁转换器（繁体 -> 简体）
cc = OpenCC("t2s")

# ==============================
# 文本标准化函数
# ==============================
def normalize_text(text):
    """繁转简 + 去空格标点 + 小写"""
    if not text:
        return ""
    text = cc.convert(text)
    text = unicodedata.normalize("NFKC", text)
    text = "".join(
        c for c in text if not (c.isspace() or unicodedata.category(c).startswith(("P", "S")))
    )
    return text.lower()

# ==============================
# 提取函数
# ==============================
def extract_region(find_file, region_name, output_file, source_label):
    """从 working.m3u 提取符合地区频道"""
    if not os.path.exists(find_file):
        print(f"⚠️ 未找到 {region_name} 的查找文件：{find_file}")
        return

    # 读取要匹配的频道名列表
    with open(find_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        search_names = [row[0].strip() for row in reader if row]

    search_norm = [normalize_text(name) for name in search_names]
    matches_dict = {name: [] for name in search_names}
    seen_urls = set()

    # 读取 M3U 内容
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

            # 遍历查找匹配
            for idx, name_norm in enumerate(search_norm):
                matched = False
                # 完全包含
                if name_norm in tvg_norm:
                    matched = True
                # 正则安全匹配
                elif re.search(re.escape(name_norm), tvg_norm):
                    matched = True
                # 模糊匹配 (相似度 >= 0.8)
                elif difflib.SequenceMatcher(None, name_norm, tvg_norm).ratio() >= 0.8:
                    matched = True

                if matched:
                    matches_dict[search_names[idx]].append([
                        search_names[idx],
                        region_name,
                        url_line,
                        source_label,
                        tvg_name_original,
                    ])
                    seen_urls.add(url_line)
                    break

            i += 2
        else:
            i += 1

    # 输出结果
    output_path = os.path.join(OUTPUT_DIR, output_file)
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["tvg-name", "地区", "URL", "来源", "原始tvg-name"])
        for name in search_names:
            writer.writerows(matches_dict[name])

    total = sum(len(v) for v in matches_dict.values())
    print(f"✅ {region_name} 匹配完成，共 {total} 个频道，输出: {output_path}")


# ==============================
# 主执行入口
# ==============================
if __name__ == "__main__":
    for region, cfg in REGIONS.items():
        extract_region(cfg["find"], region, cfg["out"], cfg["source"])
