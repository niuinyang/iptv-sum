import requests
import zipfile
import io
import os

# GitHub 仓库信息
repo_url = "https://github.com/fanmingming/live"
folder_in_repo = "tv"  # 仓库里要下载的文件夹
output_dir = "png"     # 本地保存的目录

os.makedirs(output_dir, exist_ok=True)

# 下载仓库 ZIP
zip_url = repo_url + "/archive/refs/heads/main.zip"
print(f"正在下载仓库 ZIP: {zip_url} ...")
r = requests.get(zip_url)
if r.status_code != 200:
    print(f"下载失败，状态码: {r.status_code}")
    exit(1)

# 打开 ZIP
z = zipfile.ZipFile(io.BytesIO(r.content))

# ZIP 内文件前缀
zip_root = z.namelist()[0].split('/')[0]  # 仓库压缩包的根目录名
prefix = f"{zip_root}/{folder_in_repo}/"

# 提取 tv 文件夹内容到 png
print(f"正在解压 {folder_in_repo} 文件夹到 {output_dir} ...")
for file in z.namelist():
    if file.startswith(prefix) and not file.endswith("/"):
        # 计算相对路径
        rel_path = os.path.relpath(file, prefix)
        out_path = os.path.join(output_dir, rel_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(z.read(file))

print("✅ 下载完成！")
