import requests, os, time

# ------------------- 源文件与输出路径 -------------------
sources_file = "input/network/networksource.txt"  
output_file = "output/total.m3u"
os.makedirs("output", exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0"}

all_lines = []
success, failed = 0, 0

# ------------------- 读取所有源并合并 -------------------
with open(sources_file, "r", encoding="utf-8") as f:
    for url in f:
        url = url.strip()
        if not url or url.startswith("#"):
            continue
        print(f"📡 Fetching: {url}")
        try:
            if url.startswith("http"):
                for _ in range(3):
                    try:
                        text = requests.get(url, headers=headers, timeout=10).text
                        break
                    except Exception:
                        time.sleep(2)
                else:
                    raise Exception("3次重试失败")
            else:
                with open(url, encoding="utf-8") as f2:
                    text = f2.read()

            lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#EXTM3U")]
            all_lines.extend(lines)
            success += 1
        except Exception as e:
            failed += 1
            print(f"❌ Failed: {url} ({e})")

# ------------------- 组合成 EXTINF + URL 对 -------------------
pairs = []
for i in range(len(all_lines) - 1):
    if all_lines[i].startswith("#EXTINF") and not all_lines[i+1].startswith("#"):
        pairs.append((all_lines[i], all_lines[i+1]))

# ------------------- URL 去重 -------------------
seen_urls = set()
unique_pairs = []
for title, url in pairs:
    if url not in seen_urls:
        unique_pairs.append((title, url))
        seen_urls.add(url)

# ------------------- 排序（可选） -------------------
unique_pairs.sort(key=lambda x: x[0].lower())

# ------------------- 写入 total.m3u -------------------
with open(output_file, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")
    for title, url in unique_pairs:
        f.write(f"{title}\n{url}\n")

print(f"\n✅ 合并完成：成功 {success} 源，失败 {failed} 源，去重后 {len(unique_pairs)} 条频道 → {output_file}")
