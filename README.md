# Paper Reader - 学术论文阅读助手

<div align="center">

帮助用户系统化阅读和分析学术论文，识别核心贡献、关键假设和重要洞见

</div>

---

## 功能特性

- PDF 自动解析 → 使用 MinerU API 将学术论文 PDF 转换为 Markdown 格式
- 图像智能分析 → 使用 NVIDIA NIM 中的 Kimi k2.5 多模态模型分析论文中的图表
- 结构化分析框架 → 基于"三遍阅读法"和"十个问题"的系统化阅读方法论
- 自动备份管理 → 避免重复解析，同一论文自动使用缓存
- 增量图像处理 → 边分析边保存，支持断点续传

## 目录

- [安装配置](#安装配置)
- [快速开始](#快速开始)
- [使用方法](#使用方法)
- [核心方法论](#核心方法论)
- [脚本工具](#脚本工具)
- [项目结构](#项目结构)
- [参考资源](#参考资源)

---

## 安装配置

### 1. 克隆到 Claude Skills 目录

```bash
cd ~/.claude/skills/
git clone <repo-url> paper-reader
```

或直接使用已有的 skill 目录

### 2. 安装依赖

```bash
cd ~/.claude/skills/paper-reader/scripts/
pip install requests
```

### 3. 配置 API Keys

复制 `.env.example` 并配置你的 API keys：

```bash
cd ~/.claude/skills/paper-reader/scripts/
cp .env.example .env
```

编辑 `.env` 文件：

```env
# MinerU API - 用于 PDF 解析
MINERU_API_KEY=your_mineru_api_key_here

# NVIDIA API - 用于图像分析（Kimi k2.5 模型）
NVIDIA_API_KEY=your_nvidia_api_key_here
```

**获取 API Keys**:
- [MinerU API](https://mineru.net) - 注册获取免费额度用于 PDF 解析
- [NVIDIA API](https://build.nvidia.com) - 免费提供 Kimi k2.5 等多模态模型访问

---

## 快速开始

### 使用 Claude Code

直接在 Claude Code 中触发此 skill：

```
帮助我分析这篇论文：[arxiv paper URL]
# 或
读取论文 /path/to/paper.md
```

### 命令行使用

#### 解析 PDF

```bash
cd ~/.claude/skills/paper-reader/scripts/
python3 parser.py [arxiv paper URL]
```

输出示例：

```json
{
  "markdown": "论文的markdown内容...",
  "images": ["figure1.jpg", "figure2.png", ...],
  "paper_id": "64036755",
  "backup_markdown": "/home/user/.claude/skills/paper-reader/backup/64036755/paper.md",
  "backup_images_dir": "/home/user/.claude/skills/paper-reader/backup/64036755/images"
}
```

#### 分析图像

```bash
python3 analyze_images.py \
    --paper-dir "/home/user/.claude/skills/paper-reader/backup/64036755" \
    --output "/home/user/.claude/skills/paper-reader/backup/64036755/image_analysis.json"
```

---

## 使用方法

### 工作流程

```
输入论文 (PDF/Markdown) → PDF解析 (如需) → 询问用户(图像分析?) → 深度分析 → 生成报告
```

### 步骤详解

1. **确认输入方式**
   - Markdown 文件：直接读取用户提供的文件
   - PDF URL：调用 MinerU API 解析

2. **PDF 自动解析**
   - 生成唯一论文 ID（MD5 哈希）
   - 备份到 `backup/{paper_id}/` 目录
   - 提取所有图表到 `images/` 子目录

3. **图像分析选择**
   - 选择分析图像：系统化分析所有图表
   - 跳过图像分析：基于文本快速生成摘要

4. **深度阅读分析**
   - 三遍阅读法（鸟瞰 → 理解 → 重构）
   - 沈向洋/华刚"十个问题"框架
   - 虚拟重构对比

5. **生成结构化报告**
   - 基本信息 + 5C 评估
   - 图表分析（可选）
   - 核心贡献、关键假设
   - 局限性与改进方向

---

## 核心方法论

### 三遍阅读法

#### 第一遍：鸟瞰与筛选
**目标**: 决定这篇论文是否值得读

**动作**:
- 读标题、摘要和引言
- 读结论
- 浏览章节标题了解框架
- 扫视参考文献

**时间**: 10-20 分钟

#### 第二遍：抓取逻辑与细节
**目标**: 理解论文的核心内容和逻辑流

**核心技巧**: 图像驱动深度理解

**时间**: 1-2 小时

#### 第三遍：虚拟复现
**目标**: 彻底掌握，达到可以审稿或基于此做研究的程度

**核心技巧**: 虚拟重构（先自己想方案，再对比作者）

**时间**: 数小时至数天

### 沈向洋/华刚"十个问题"

**关于问题本身**:
1. Input/Output - 输入和输出是什么？
2. Novelty - 全新问题还是旧问题的新解法？
3. Importance - 为什么这个问题现在依然重要？

**关于解决方案与相关工作**:
4. Related Work - 关键人物和相关研究
5. Solution - 核心技术方案
6. Experiments - 实验设计和质量

**关于验证与评价**:
7. Data - 数据集选择和可信度
8. Validation - 实验结果对假设的支持力度

**关于总结与展望**:
9. Contribution - 客观认定的贡献
10. Next Step - 潜在的后续工作方向

### 阅读四段位

1. **消极阅读** - 像海绵一样被动吸收
2. **积极阅读** - 思考"这些知识对我有什么用？"
3. **批判性阅读** - 像审稿人一样挑刺，问"Is this bullshit?"
4. **创造性阅读** - 从别人的"失败"中发现新的研究方向

---

## 脚本工具

### parser.py

PDF 解析和自动备份工具

```bash
python3 parser.py <PDF_URL>
```

**特性**:
- 自动生成论文 ID（基于文件名 MD5）
- 避免重复解析（相同 PDF 使用缓存）
- 提取所有图像文件
- 支持自定义输出目录

### analyze_images.py

批量图像分析工具

```bash
python3 analyze_images.py \
    --paper-dir <PAPER_DIR> \
    --output <OUTPUT_JSON>
```

**参数**:
- `--paper-dir`: 论文目录路径
- `--output`: 输出 JSON 分析结果路径
- `--context-lines`: 上下文提取行数（默认 10）

**分析框架**:
1. 图像类型识别（架构图、流程图、实验结果图等）
2. 核心信息提取（关键结论、坐标轴含义）
3. 数据观察（趋势、异常点）
4. 与文字对应（一致性验证）
5. 潜在问题（误导性、误差线标注）

---

## 项目结构

```
paper-reader/
├── SKILL.md              # Skill 定义文件
├── README.md             # 项目说明文档（本文件）
├── references/           # 专家指导文档
│   └── expert_guidance.md
├── scripts/              # 脚本工具
│   ├── parser.py         # PDF 解析脚本
│   ├── analyze_images.py # 图像分析脚本
│   └── .env.example          # API Keys 配置模板
└── backup/               # 论文备份目录
    └── {paper_id}/       # 每篇论文独立的备份文件夹
        ├── paper.md      # 论文 markdown 内容
        ├── images/       # 提取的图像文件
        └── image_analysis.json  # 图像分析结果
```

---

## 输出示例

### 完整的论文阅读报告

```markdown
# 论文阅读报告

## 基本信息
- 标题：[论文标题]
- 作者：[作者列表]
- 发表年份/期刊/会议：[发表信息]
- 论文ID：[paper_id]

## 一句话总结
[核心贡献的一句话概括]

## 5C评估
- **Category**: 计算机视觉 / 自然语言处理 / ...
- **Context**: 研究背景和动机
- **Correctness**: 论文的正确性评估
- **Contribution**: 核心贡献点
- **Clarity**: 论文表述的清晰程度

## 图表分析
[从 image_analysis.json 整理的图像分析内容]

## 沈向洋/华刚十个问题分析
[系统化的十个问题回答]

## 核心贡献
1. ...
2. ...

## 关键假设
- ...

## 方法概述
...

## 局限性
- ...

## 虚拟重构对比
如果我是作者，我会：...

## 个人思考
- 当前阅读阶段：[消极/积极/批判性/创造性]
```

---

## 参考资源

本 skill 整合了以下专家的核心方法论：

- **王鑫**: 如何阅读学术论文 - (https://qclab.wang/post/reading/)
- **沈向洋、华刚**: 读科研论文的三个层次、四个阶段与十个问题-(https://zhuanlan.zhihu.com/p/163227375)
- **S. Keshav**: "How to Read a Paper"-(https://www.eecs.harvard.edu/~michaelm/postscripts/ReadPaper.pdf)
- **york.ac.uk**: "Being critical: Reading academic articles" - (https://subjectguides.york.ac.uk/critical/articles)

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

## 许可证

MIT License

---

## 致谢

感谢上述专家提供的论文阅读方法论指导，以及 Claude Code 平台提供的 skill 扩展机制。

