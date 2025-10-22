import requests, os

sources_file = "m3u_sources/list.txt"
output_file = "output/total.m3u"

os.makedirs("output", exist_ok=True)

# ------------------- 读取所有源并合并 -------------------
all_lines = []

with open(sources_file, "r", encoding="utf-8") as f:
    for url in f:
        url = url.strip()
        if not url or url.startswith("#"):
            continue
        print(f"📡 Fetching: {url}")
        try:
            if url.startswith("http"):
                text = requests.get(url, timeout=10).text
            else:
                with open(url, encoding="utf-8") as f2:
                    text = f2.read()
            # 忽略文件头 #EXTM3U
            all_lines.extend([l for l in text.splitlines() if not l.strip().startswith("#EXTM3U")])
        except Exception as e:
            print(f"❌ Failed: {url} ({e})")

# ------------------- 组合成 EXTINF + URL 对 -------------------
pairs = [(all_lines[i], all_lines[i+1]) for i in range(len(all_lines)-1) if all_lines[i].startswith("#EXTINF")]

# ------------------- URL 去重 -------------------
seen_urls = set()
unique_pairs = []
for title, url in pairs:
    if url not in seen_urls:
        unique_pairs.append((title, url))
        seen_urls.add(url)

# ------------------- 写入 total.m3u -------------------
with open(output_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for title, url in unique_pairs:
        f.write(f"{title}\n{url}\n")

print(f"✅ 合并完成（去重后 {len(unique_pairs)} 条源）: {output_file}")
