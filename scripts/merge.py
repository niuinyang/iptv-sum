import requests, os, time, re

# ------------------- 配置 -------------------
sources_file = "input/network/networksource.txt"
output_file = "output/total.m3u"
os.makedirs("output", exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0"}
all_lines = []
success, failed = 0, 0

# ------------------- 读取源列表 -------------------
with open(sources_file, "r", encoding="utf-8") as f:
    urls = [u.strip() for u in f if u.strip() and not u.strip().startswith("#")]

for url in urls:
    print(f"📡 Fetching: {url}")
    try:
        if url.startswith("http"):
            text = None
            for attempt in range(3):
                try:
                    r = requests.get(url, headers=headers, timeout=15)
                    r.encoding = r.apparent_encoding or "utf-8"
                    text = r.text
                    break
                except Exception as e:
                    print(f"⚠️ 重试 {attempt+1}/3 失败: {e}")
                    time.sleep(2)
            if text is None:
                raise Exception("3次重试失败")
        else:
            with open(url, encoding="utf-8", errors="ignore") as f2:
                text = f2.read()

        # 保留所有行，去掉文件头 #EXTM3U
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#EXTM3U")]
        all_lines.extend(lines)
        success += 1
    except Exception as e:
        failed += 1
        print(f"❌ Failed: {url} ({e})")

# ------------------- 组合 EXTINF + URL 对 -------------------
pairs = []
url_pattern = re.compile(r'^https?://')
for i, line in enumerate(all_lines):
    if line.startswith("#EXTINF"):
        # 向下找第一个 URL
        for j in range(i+1, len(all_lines)):
            if url_pattern.match(all_lines[j]):
                pairs.append((line, all_lines[j]))
                break

# ------------------- 去重 (完全重复的 EXTINF+URL) -------------------
seen = set()
unique_pairs = []
for title, url in pairs:
    key = (title, url)
    if key not in seen:
        unique_pairs.append((title, url))
        seen.add(key)

# ------------------- 自然排序 -------------------
def natural_key(text):
    return [int(t) if t.isdigit() else t.lower() for t in re.split("([0-9]+)", text)]

unique_pairs.sort(key=lambda x: natural_key(x[0]))

# ------------------- 写入 total.m3u -------------------
with open(output_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for title, url in unique_pairs:
        f.write(f"{title}\n{url}\n")

print(f"\n✅ 合并完成：成功 {success} 源，失败 {failed} 源，"
      f"去重后 {len(unique_pairs)} 条频道 → {output_file}")
