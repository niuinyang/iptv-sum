# ...前面的代码保持不变...

# 遍历搜索列表，看是否匹配
for idx, name_norm in enumerate(search_norm):
    if name_norm in tvg_norm:
        # 第一列 find.csv 名称，第二列地区，第三列 URL，第四列来源（固定“台湾源”），第五列原始 tvg-name
        matches_dict[search_names[idx]].append([
            search_names[idx], 
            "台湾", 
            url_line, 
            "台湾源", 
            tvg_name_original
        ])
        seen_urls.add(url_line)
        break

# 按 find.csv 顺序写入 CSV
with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["tvg-name", "地区", "URL", "来源", "原始tvg-name"])
    for name in search_names:
        writer.writerows(matches_dict[name])

print(f"匹配完成，共找到 {sum(len(v) for v in matches_dict.values())} 个频道，已输出到 {output_file}")
