#!/usr/bin/env python3
"""MinerU PDF 解析脚本

使用 MinerU API 将 PDF 解析为 Markdown 格式
"""

import os
import sys
import json
import requests
import zipfile
import time
import tempfile
import hashlib
from pathlib import Path


def get_paper_id(pdf_url):
    """从 PDF URL 生成唯一的论文 ID（使用 MD5 哈希）

    Args:
        pdf_url: PDF 文件 URL

    Returns:
        str: 唯一的论文 ID（8位十六进制）
    """
    # 从 URL 提取文件名（不含扩展名），如果无法提取则使用完整 URL
    url_path = pdf_url.rstrip('/')
    filename = url_path.split('/')[-1]
    name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else url_path

    # 使用文件名或 URL 生成 MD5 哈希
    hash_obj = hashlib.md5(name_without_ext.encode('utf-8'))
    return hash_obj.hexdigest()[:64]


def read_api_key():
    """从 .env 文件读取 API key"""
    env_path = Path(__file__).parent / '.env'
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('MINERU_API_KEY'):
                key = line.split('=', 1)[1].strip().strip('"\'')
                return key
    raise ValueError("MINERU_API_KEY not found in .env file")


def submit_task(pdf_url, api_key):
    """提交 PDF 解析任务到 MinerU API，返回 task_id"""
    url = "https://mineru.net/api/v4/extract/task"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "url": pdf_url,
        "model_version": "vlm"
    }

    try:
        print(f"正在提交解析任务: {pdf_url}", file=sys.stderr)
        response = requests.post(url, headers=headers, json=data, timeout=300)
        response.raise_for_status()

        result = response.json()
        print(f"任务提交响应: {json.dumps(result, indent=2)}", file=sys.stderr)

        if 'data' in result and 'task_id' in result['data']:
            return result['data']['task_id']
        elif 'task_id' in result:
            return result['task_id']
        else:
            print("API Response structure:", json.dumps(result, indent=2), file=sys.stderr)
            raise ValueError("task_id not found in API response")

    except requests.exceptions.RequestException as e:
        print(f"提交任务失败: {e}", file=sys.stderr)
        raise


def check_task_status(task_id, api_key):
    """检查任务状态，返回状态信息"""
    url = f"https://mineru.net/api/v4/extract/task/{task_id}"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.get(url, headers=headers, timeout=300)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        print(f"检查任务状态失败: {e}", file=sys.stderr)
        raise


def wait_for_completion(task_id, api_key, check_interval=30):
    """等待任务完成，返回任务结果"""
    print(f"开始轮询任务状态，task_id: {task_id}", file=sys.stderr)

    while True:
        try:
            result = check_task_status(task_id, api_key)

            if 'data' in result:
                status_info = result['data']
            else:
                status_info = result

            status = status_info.get('state', '')
            print(f"任务状态: {status}", file=sys.stderr)

            if status == 'done':
                print("任务已完成", file=sys.stderr)
                return status_info
            elif status == 'failed':
                error_msg = status_info.get('error', 'Unknown error')
                raise ValueError(f"任务失败: {error_msg}")

            # 继续轮询
            print(f"等待 {check_interval} 秒后重新检查...", file=sys.stderr)
            time.sleep(check_interval)

        except requests.exceptions.RequestException as e:
            print(f"轮询时出错: {e}，将在 {check_interval} 秒后重试", file=sys.stderr)
            time.sleep(check_interval)


def download_and_extract_zip(full_zip_url, api_key, pdf_url=None, output_dir=None, save_content=True):
    """下载 ZIP 文件并提取 Markdown 内容和图像路径

    Args:
        full_zip_url: ZIP 文件下载 URL
        api_key: API 密钥
        pdf_url: 原始 PDF URL，用于生成唯一论文 ID
        output_dir: 可选，保存文件的目录
        save_content: 是否保存内容到文件

    Returns:
        tuple: (markdown_content, image_paths) 其中 image_paths 是图像文件路径列表
    """
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    # 获取skill根目录，创建备份文件夹
    skill_root = Path(__file__).parent.parent
    backup_base_dir = skill_root / 'backup'
    backup_base_dir.mkdir(parents=True, exist_ok=True)

    # 为每篇论文创建独立的备份文件夹
    if pdf_url:
        paper_id = get_paper_id(pdf_url)
        backup_dir = backup_base_dir / paper_id
    else:
        # 如果没有提供 pdf_url，使用 ZIP URL 的哈希值
        paper_id = get_paper_id(full_zip_url)
        backup_dir = backup_base_dir / paper_id

    backup_dir.mkdir(parents=True, exist_ok=True)
    print(f"论文备份目录: {backup_dir} (ID: {paper_id})", file=sys.stderr)

    import shutil

    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
        tmp_zip_path = tmp_zip.name

    try:
        print(f"正在下载解析结果: {full_zip_url}", file=sys.stderr)
        response = requests.get(full_zip_url, headers=headers, stream=True)
        response.raise_for_status()

        # 写入临时文件
        with open(tmp_zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # 解压 ZIP 文件
        print("正在解压 ZIP 文件...", file=sys.stderr)
        with zipfile.ZipFile(tmp_zip_path, 'r') as zip_ref:
            # 提取到临时目录
            with tempfile.TemporaryDirectory() as tmp_dir:
                zip_ref.extractall(tmp_dir)

                # 查找 Markdown 文件
                md_files = list(Path(tmp_dir).rglob('*.md'))
                if not md_files:
                    raise ValueError("ZIP 文件中未找到 Markdown 文件")

                # 通常是主要的 markdown 文件
                md_file = md_files[0]
                print(f"找到 Markdown 文件: {md_file}", file=sys.stderr)

                # 查找所有图像文件
                image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
                image_files = [
                    img for img in Path(tmp_dir).rglob('*')
                    if img.is_file() and img.suffix.lower() in image_extensions
                ]

                print(f"找到 {len(image_files)} 个图像文件", file=sys.stderr)

                # 创建论文专用的 images 目录
                backup_images_dir = backup_dir / 'images'
                backup_images_dir.mkdir(parents=True, exist_ok=True)

                # 清空该论文的备份图像目录
                if backup_images_dir.exists():
                    for item in backup_images_dir.iterdir():
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)

                # 复制图像文件到备份目录
                for img_file in image_files:
                    relative_path = img_file.relative_to(tmp_dir)
                    dest_path = backup_images_dir / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(img_file, dest_path)

                # 复制md文件到备份文件夹
                backup_md_file = backup_dir / 'paper.md'
                shutil.copy2(md_file, backup_md_file)

                print(f"已备份论文 {paper_id} 到: {backup_dir}", file=sys.stderr)
                print(f"- Markdown: {backup_md_file}", file=sys.stderr)
                print(f"- 图像: {backup_images_dir} ({len(image_files)} 个文件)", file=sys.stderr)

                # 从备份文件夹读取 markdown 内容
                with open(backup_md_file, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()

                # 获取图像相对于备份目录的路径列表
                image_paths = [
                    str(img.relative_to(backup_images_dir))
                    for img in backup_images_dir.rglob('*')
                    if img.is_file() and img.suffix.lower() in image_extensions
                ]

                # 如果指定了输出目录，保存内容
                if output_dir and save_content:
                    output_path = Path(output_dir)
                    output_path.mkdir(parents=True, exist_ok=True)

                    # 从备份目录复制到输出目录
                    md_output_path = output_path / 'paper.md'
                    shutil.copy2(backup_md_file, md_output_path)

                    # 复制图像目录
                    images_dir = output_path / 'images'
                    shutil.rmtree(images_dir) if images_dir.exists() else None
                    shutil.copytree(backup_images_dir, images_dir)

                    saved_image_paths = [
                        str(images_dir / rel_path)
                        for rel_path in image_paths
                    ]

                    print(f"已将内容保存到: {output_path}", file=sys.stderr)
                    print(f"- Markdown: {md_output_path}", file=sys.stderr)
                    print(f"- 图像: {images_dir} ({len(saved_image_paths)} 个文件)", file=sys.stderr)

                    # 返回保存的路径信息
                    return {
                        "paper_id": paper_id,
                        "markdown_file": str(md_output_path),
                        "images_dir": str(images_dir),
                        "image_files": saved_image_paths,
                        "backup_markdown": str(backup_md_file),
                        "backup_images_dir": str(backup_images_dir),
                        "backup_dir": str(backup_dir),  # 添加论文备份目录路径
                        "markdown_content": markdown_content  # 同时保留内容供直接使用
                    }

                # 返回备份路径信息和内容
                return {
                    "paper_id": paper_id,
                    "backup_markdown": str(backup_md_file),
                    "backup_images_dir": str(backup_images_dir),
                    "backup_dir": str(backup_dir),  # 添加论文备份目录路径
                    "image_files": [str(backup_images_dir / p) for p in image_paths],
                    "markdown_content": markdown_content,
                    "image_paths": image_paths
                }

    finally:
        # 清理临时文件
        if os.path.exists(tmp_zip_path):
            os.unlink(tmp_zip_path)


def parse_pdf(pdf_url, api_key, output_dir=None):
    """调用 MinerU API 解析 PDF（支持异步任务）

    Args:
        pdf_url: PDF 文件 URL
        api_key: API 密钥
        output_dir: 可选，保存文件的目录

    Returns:
        如果指定了 output_dir，返回字典包含文件路径信息
        否则返回 tuple: (markdown_content, image_paths)
    """
    # 1. 提交任务
    task_id = submit_task(pdf_url, api_key)

    # 2. 等待任务完成（每30秒检查一次）
    task_result = wait_for_completion(task_id, api_key, check_interval=30)

    # 3. 下载并提取结果
    full_zip_url = task_result.get('full_zip_url')
    if not full_zip_url:
        raise ValueError("任务结果中未找到 full_zip_url")

    result = download_and_extract_zip(full_zip_url, api_key, pdf_url, output_dir)

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python parser.py <PDF_URL> [OUTPUT_DIR]", file=sys.stderr)
        print("Example: python parser.py https://arxiv.org/pdf/2602.12852v1 /tmp/paper_output", file=sys.stderr)
        sys.exit(1)

    pdf_url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    api_key = read_api_key()

    try:
        result = parse_pdf(pdf_url, api_key, output_dir)

        # 以 JSON 格式输出结果
        # download_and_extract_zip 总是返回字典
        if 'markdown_file' in result:
            # 已保存到指定输出目录的情况
            output = {
                "markdown_file": result['markdown_file'],
                "images_dir": result['images_dir'],
                "image_files": result['image_files'],
                "markdown": result['markdown_content'],
                "paper_dir": result['backup_dir']  # 使用备份目录作为论文目录
            }
        else:
            # 仅保存到 backup 目录的情况
            output = {
                "markdown": result['markdown_content'],
                "images": result.get('image_files', []),
                "paper_dir": result['backup_dir']  # 使用备份目录作为论文目录
            }

        print(json.dumps(output, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
