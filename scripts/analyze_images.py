#!/usr/bin/env python3
"""学术论文图像分析脚本

结合图像和上下文文字，使用多模态模型进行分析
支持模型: kimi (moonshotai/kimi-k2.5), qwen (qwen/qwen3.5-397b-a17b)
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

try:
    import requests
except ImportError:
    print("Error: requests is required. Install with: pip install requests", file=sys.stderr)
    sys.exit(1)


def read_nvidia_api_key():
    """从 .env 文件读取 NVIDIA API key"""
    env_path = Path(__file__).parent / '.env'
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('NVIDIA_API_KEY'):
                key = line.split('=', 1)[1].strip().strip('"\'')
                return key
    raise ValueError("NVIDIA_API_KEY not found in .env file. Please add it to enable image analysis.")


def find_image_context(image_path: Path, markdown_content: str, context_lines: int = 50) -> str:
    """根据图像文件名在 markdown 中定位上下文

    Args:
        image_path: 图像文件路径
        markdown_content: Markdown 内容
        context_lines: 前后上下文行数

    Returns:
        上下文文本
    """
    # 提取图像文件名（不含扩展名）
    image_name = image_path.stem.lower()
    image_filename = image_path.name.lower()

    lines = markdown_content.split('\n')
    best_matches = []

    for i, line in enumerate(lines):
        line_lower = line.lower()
        # 查找图像引用（多种常见格式）
        if (image_name in line_lower or
            image_filename in line_lower or
            f"![{image_name}" in line_lower or
            f"figure {image_name}" in line_lower or
            f"fig. {image_name}" in line_lower or
            f"fig{image_name}" in line_lower):
            best_matches.append(i)

    if not best_matches:
        return None

    # 取第一个匹配位置
    line_num = best_matches[0]
    start = max(0, line_num - context_lines)
    end = min(len(lines), line_num + context_lines + 1)

    context_lines_list = lines[start:end]
    return '\n'.join(f"{i+1}. {line}" for i, line in enumerate(context_lines_list, start=start))


def build_analysis_prompt(context_text: str) -> str:
    """构建图像分析提示词"""
    return f"""请分析以下学术论文图像，结合其上下文描述进行深入解读：

**上下文文字内容**：
{context_text}

**分析任务**：
1. **图像类型识别**：这是什么类型的图表？（架构图、流程图、实验结果图、对比图、数据可视化等）
2. **核心信息提取**：
   - 图表想要传达的关键结论是什么？
   - 坐标轴代表什么含义？X 轴和 Y 轴分别表示什么？
   - 如果是对比图，哪个方法表现最好？提升幅度是多少？
3. **数据观察**：
   - 图中的趋势是什么？（上升、下降、收敛、波动等）
   - 是否有显著的异常点或特殊情况？
4. **与文字对应**：
   - 图中的结论是否与上下文描述一致？
   - 作者从图中得出的推论是否合理？
5. **潜在问题**：
   - 图表是否有误导性？（如 Y 轴截断、刻度不合理等）
   - 误差线是否被适当标注？
   - 数据点是否足够密集？

请以结构化的方式（使用 Markdown）返回分析结果。"""


def read_image_as_base64(image_path: Path) -> str:
    """读取图像文件并转换为 base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def call_vision_model(image_path: Path, context_text: str, api_key: str, model: str = "kimi", timeout: int = 600) -> str:
    """调用 NVIDIA NIM 的多模态 API 分析图像

    Args:
        image_path: 图像文件路径
        context_text: 上下文文本
        api_key: NVIDIA API key
        model: 模型选择，支持 "kimi" 或 "qwen"，默认 "kimi"
        timeout: 请求超时时间（秒）

    Returns:
        分析结果
    """
    prompt = build_analysis_prompt(context_text)
    image_data = read_image_as_base64(image_path)

    url = "https://integrate.api.nvidia.com/v1/chat/completions"

    # 配置不同模型的参数
    model_configs = {
        "kimi": {
            "model": "moonshotai/kimi-k2.5",
            "temperature": 0.3,
            "top_p": 1.00,
            "chat_template_kwargs": {"thinking": True}
        },
        "qwen": {
            "model": "qwen/qwen3.5-397b-a17b",
            "temperature": 0.60,
            "top_p": 0.95,
            "top_k": 20,
            "presence_penalty": 0,
            "repetition_penalty": 1,
            "chat_template_kwargs": {"enable_thinking": True}
        }
    }

    if model not in model_configs:
        raise ValueError(f"不支持的模型: {model}。支持的模型: kimi, qwen")

    config = model_configs[model]

    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_data}"}
                    }
                ]
            }
        ],
        "max_tokens": 16384,
        "temperature": config["temperature"],
        "top_p": config["top_p"],
        "stream": False
    }

    # 添加模型特定参数
    if "top_k" in config:
        payload["top_k"] = config["top_k"]
    if "presence_penalty" in config:
        payload["presence_penalty"] = config["presence_penalty"]
    if "repetition_penalty" in config:
        payload["repetition_penalty"] = config["repetition_penalty"]
    payload["chat_template_kwargs"] = config["chat_template_kwargs"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']


def analyze_image(image_path: Path, markdown_content: str, api_key: str, model: str = "kimi", current_index: int = 0, total_images: int = 0) -> Dict:
    """分析单个图像

    Args:
        image_path: 图像文件路径
        markdown_content: Markdown 内容
        api_key: NVIDIA API key
        current_index: 当前图像索引（从1开始）
        total_images: 总图像数量

    Returns:
        分析结果字典
    """
    print(f"正在分析图像: {image_path.name} ({current_index}/{total_images})", file=sys.stderr)

    try:
        # 1. 定位上下文
        context = find_image_context(image_path, markdown_content)

        if not context:
            print(f"  - 跳过: {image_path.name} (未找到上下文)", file=sys.stderr)
            return {
                "image_path": str(image_path),
                "image_name": image_path.name,
                "context_preview": context[:500] + "..." if context and len(context) > 500 else (context or ""),
                "context_found": False,
                "skipped": True,
                "skip_reason": "未在 markdown 中找到该图像的上下文描述",
                "progress": {
                    "current": current_index,
                    "total": total_images
                }
            }

        print(context)
        # 2. 调用选定的视觉模型分析
        analysis = call_vision_model(image_path, context, api_key, model)
        print(analysis)
        print(f"  - 完成: {image_path.name} ({current_index}/{total_images})", file=sys.stderr)

        return {
            "image_path": str(image_path),
            "image_name": image_path.name,
            "context_preview": context[:500] + "..." if len(context) > 500 else context,
            "context_found": True,
            "analysis": analysis,
            "progress": {
                "current": current_index,
                "total": total_images
            }
        }

    except Exception as e:
        print(f"  - 失败: {e}", file=sys.stderr)
        return {
            "image_path": str(image_path),
            "image_name": image_path.name,
            "error": str(e),
            "progress": {
                "current": current_index,
                "total": total_images
            }
        }


def collect_images(images_dir: Path, markdown_content: str = None) -> List[Path]:
    """收集图像文件，从 backup 文件夹中的 md 文件按顺序找出图像文件名
    只保留在 images 目录下出现的图像

    Args:
        images_dir: 图像目录路径
        markdown_content: Markdown 内容（可选），用于按顺序提取图像引用

    Returns:
        按顺序排列且实际存在的图像文件列表
    """
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
    images = []

    # 先收集 images 目录中实际存在的所有图像文件
    if images_dir.is_file():
        # 单个文件
        if images_dir.suffix.lower() in image_extensions:
            return [images_dir]
        else:
            raise ValueError(f"提供的文件不是支持的图像类型: {images_dir}")
    else:
        # 目录
        for path in images_dir.rglob('*'):
            if path.is_file() and path.suffix.lower() in image_extensions:
                images.append(path)

    # 如果没有提供 markdown 内容，直接按文件名排序返回所有图像
    if not markdown_content:
        return sorted(images)

    # 从 markdown 中按顺序提取图像文件名
    import re
    md_image_names = []

    # 匹配多种格式的图像引用
    image_patterns = [
        r'!\[.*?\]\(([^)]+\.(?:png|jpg|jpeg|gif|bmp|tiff|webp))\)',  # markdown image syntax
        r'<image:([^>]+)>',  # <image:filename> format
        r'!\[image\]\(([^)]+)\)',  # ![image](filename) format
    ]

    # 按内容顺序查找所有匹配
    for pattern in image_patterns:
        matches = re.finditer(pattern, markdown_content, re.IGNORECASE)
        for match in matches:
            image_path = match.group(1)
            # 提取文件名（去除路径）
            filename = Path(image_path).name
            if filename not in md_image_names:
                md_image_names.append(filename)

    # 构建images目录的文件名映射（不区分大小写）
    images_lower_to_path = {img.name.lower(): img for img in images}

    # 按markdown中的顺序，只保留在images目录中实际存在的图像
    ordered_images = []
    for name in md_image_names:
        name_lower = name.lower()
        if name_lower in images_lower_to_path:
            ordered_images.append(images_lower_to_path[name_lower])

    return ordered_images


def main():
    parser = argparse.ArgumentParser(description='学术论文图像分析工具')
    parser.add_argument('--paper-dir', required=True, help='论文目录路径（包含 paper.md 和 images 文件夹）')
    parser.add_argument('--output', required=True, help='输出 JSON 文件路径')
    parser.add_argument('--context-lines', type=int, default=10, help='上下文提取行数（默认：10）')
    parser.add_argument('--model', type=str, default='qwen', choices=['kimi', 'qwen'], help='使用的视觉模型（默认：qwen）')
    args = parser.parse_args()

    paper_dir = Path(args.paper_dir)

    # 自动解析论文目录
    # 1. 查找 markdown 文件 (paper.md)
    markdown_path = paper_dir / 'paper.md'
    if not markdown_path.exists():
        # 尝试查找任意 .md 文件
        md_files = list(paper_dir.glob('*.md'))
        if not md_files:
            print(f"错误: 在 {paper_dir} 中未找到 paper.md 文件", file=sys.stderr)
            sys.exit(1)
        markdown_path = md_files[0]

    # 读取 markdown 内容
    with open(markdown_path, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    # 2. 查找 images 目录 (可能是 images/ 或 images/images/)
    images_dir = paper_dir / 'images'
    if not images_dir.exists():
        print(f"错误: 在 {paper_dir} 中未找到 images 目录", file=sys.stderr)
        sys.exit(1)

    # 检查是否是嵌套的 images/images/ 结构
    nested_images_dir = images_dir / 'images'
    if nested_images_dir.exists() and nested_images_dir.is_dir():
        images_dir = nested_images_dir

    # 3. 设置输出文件路径
    output_path = Path(args.output)

    # 收集图像
    images = collect_images(images_dir, markdown_content)
    if not images:
        print(f"错误: 在 {images_dir} 中未找到图像文件", file=sys.stderr)
        sys.exit(1)

    print(f"找到 {len(images)} 个图像文件", file=sys.stderr)

    # 读取 API key
    try:
        api_key = read_nvidia_api_key()
    except ValueError as e:
        print(f"警告: {e}", file=sys.stderr)
        print("图像分析功能将跳过，仅返回图像列表", file=sys.stderr)
        api_key = None

    # 初始化输出文件结构
    output_data = {
        "model": args.model,
        "model_full_name": "moonshotai/kimi-k2.5" if args.model == "kimi" else "qwen/qwen3.5-397b-a17b",
        "total_images": len(images),
        "analyzed_images": 0,
        "skipped_images": 0,
        "failed_images": 0,
        "results": []
    }

    # 创建目录并初始化输出文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    def save_progress():
        """保存当前进度到JSON文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

    # 初始保存（空的results）
    save_progress()

    # 分析所有图像 - 每分析一个就保存一次
    for i, image_path in enumerate(images, 1):
        print(f"[{i}/{len(images)}]", file=sys.stderr, end=' ')

        if api_key:
            analysis = analyze_image(image_path, markdown_content, api_key, args.model, i, len(images))
        else:
            analysis = {
                "image_path": str(image_path),
                "image_name": image_path.name,
                "error": "NVIDIA_API_KEY 未配置",
                "progress": {
                    "current": i,
                    "total": len(images)
                }
            }

        # 添加到结果列表
        output_data["results"].append(analysis)

        # 更新统计
        if "error" not in analysis:
            if analysis.get("skipped") == True:
                output_data["skipped_images"] += 1
            else:
                output_data["analyzed_images"] += 1
        else:
            output_data["failed_images"] += 1

        # 立即保存进度
        save_progress()

    print(f"\n分析完成！结果已保存到: {output_path}", file=sys.stderr)
    print(f"成功分析: {output_data['analyzed_images']}/{output_data['total_images']}", file=sys.stderr)
    print(f"跳过图像: {output_data['skipped_images']}/{output_data['total_images']} (未找到上下文)", file=sys.stderr)
    print(f"分析失败: {output_data['failed_images']}/{output_data['total_images']}", file=sys.stderr)


if __name__ == "__main__":
    main()
