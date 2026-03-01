---
name: paper-reader
description: 学术论文阅读助手。帮助用户系统化阅读和分析学术论文，识别核心贡献、关键假设和重要洞见。当用户提供一个包含论文内容的markdown文件，或请求阅读、分析、理解论文时触发此skill。支持从PDF URL通过mineru解析论文。触发词包括：读论文、论文阅读、paper reading、analyze paper、论文分析、学术阅读、文献阅读。
---

# 论文阅读助手

帮助用户系统化阅读和分析学术论文，提取核心贡献、关键假设和重要洞见。所有代码实现都在 scripts 目录下。

## 配置

在使用 PDF URL 和图像分析功能前，需要在 skill 目录下创建 `.env` 文件并添加 API keys：

```bash
在 `~/.claude/skills/paper-reader/scripts/.env` 文件中添加：

# MinerU API - 用于 PDF 解析
MINERU_API_KEY=your_mineru_api_key_here

# NVIDIA API - 用于图像分析（调用 NVIDIA NIM 中的 Kimi k2.5 模型）
NVIDIA_API_KEY=your_nvidia_api_key_here
```

**获取 API Keys**:
- MinerU API Key: 从 https://mineru.net 注册获取
- NVIDIA API Key: 从 https://build.nvidia.com 注册获取（免费提供 Kimi k2.5 模型访问）

## 工作流程

### 1. 确认输入方式

首先确认论文的输入方式：

- **Markdown 文件**: 用户已提供或提供包含论文内容的 markdown 文件路径
- **PDF URL**: 用户提供论文 PDF 的 URL，将通过 mineru 解析

### 2. PDF URL 解析（如适用）

**重要**: `parser.py` 已整合完整的 PDF 解析和图像提取功能。

#### 2.1 使用 parser.py 解析 PDF

`parser.py` 会自动：
1. 调用 MinerU API 解析 PDF
2. 生成本地唯一论文 ID（基于 MD5 哈希）
3. 在 `backup/{paper_id}/` 目录下创建备份文件夹
4. 保存论文 markdown 内容为 `paper.md`
5. 提取所有图像到 `backup/{paper_id}/images/` 目录

```bash
cd ~/.claude/skills/paper-reader/scripts/
python3 parser.py "PDF_URL"
```

**返回的 JSON 格式**：

```json
{
  "markdown": "论文的 markdown 内容...",
  "images": ["图像文件路径列表"],
  "paper_dir": "/path/to/backup/{paper_id}"
}
```

**输出说明**：
- `markdown`: 论文的完整 markdown 内容
- `images`: 论文中包含的所有图像文件路径列表
- `paper_dir`: 论文备份目录路径（包含 `paper.md` 和 `images/` 文件夹），可直接传给 `analyze_images.py` 的 `--paper-dir` 参数

#### 2.2 备份目录结构

解析后的论文自动备份到 `backup/` 目录：

```
~/.claude/skills/paper-reader/backup/
└── {paper_id}/
    ├── paper.md           # 论文 markdown 内容
    └── images/           # 论文所有图像
        ├── figure1.jpg
        ├── figure2.png
        └── ...
```

**避免重复解析**: 任何同一 PDF URL（或相同内容的 PDF）会生成相同的 `paper_id`，会直接使用已存在的备份内容。

#### 2.3 完整解析示例

```bash
# 解析 PDF（自动备份到 backup 目录）
cd ~/.claude/skills/paper-reader/scripts/
python3 parser.py "https://arxiv.org/pdf/2602.12852v1"

# 输出示例:
# {
#   "markdown": "论文的 markdown 内容...",
#   "images": ["图像文件路径列表"],
#   "paper_dir": "/home/user/.claude/skills/paper-reader/backup/64036755"
# }

# 后续可直接使用 paper_dir 进行图像分析：
# python3 analyze_images.py --paper-dir /home/user/.claude/skills/paper-reader/backup/64036755 --output .../image_analysis.json
```

### 3. 询问图像分析偏好

在开始深度阅读前，使用 AskUserQuestion 工具询问用户是否需要分析论文中的图像：

```
问题：是否需要分析论文中的图像内容？
选项：
- 分析图像（推荐）：系统化分析所有图表，生成完整的图像分析报告
- 跳过图像分析：跳过图像分析步骤，快速生成基于文本的论文摘要
```

**用户选择记录**: 记录用户的选择以指导后续流程（`analyze_images: true/false`）

### 4. 读取论文内容

根据输入方式使用 Read 工具读取论文内容：

- **Markdown 文件**: 直接读取用户提供的文件
- **PDF URL 解析后**: 读取 `backup/{paper_id}/paper.md` 文件

### 5. 读取备份目录（如果适用）

当已有备份时，可以直接访问：

```bash
# 查看 backup 目录中的所有论文
ls ~/.claude/skills/paper-reader/backup/

# 读取某篇论文的 markdown
cat ~/.claude/skills/paper-reader/backup/{paper_id}/paper.md

# 查看某篇论文的图像
ls ~/.claude/skills/paper-reader/backup/{paper_id}/images/
```

### 5. 核心理念：打破线性阅读

学术论文绝不应该从头读到尾（Start-to-end）：

- **非线性阅读**: 像剥洋葱一样，由表及里，分层次阅读
- **主动阅读**: 带着问题读，而不是被动接收信息
- **重构思维**: 读论文的最终目的是为了"写"和"创造"。不仅要理解作者做了什么，还要思考"如果是我，我会怎么做"

### 6. 三遍阅读法 (The Three-Pass Approach)

阅读一篇论文应分为三个递进的层次。

#### 第一遍：鸟瞰与筛选 (Scanning / 10-20分钟)

**目标**: 决定这篇论文是否值得读，通过分类（Category）、背景（Context）、正确性（Correctness）、贡献（Contribution）和清晰度（Clarity）来评估。

**动作**:
- 读标题、摘要和引言
- 读结论
- 浏览章节标题了解框架
- 扫视参考文献，看是否有你熟悉的经典工作

**决策输出**: 此时你应该能回答：
- 这篇论文在解决什么问题？
- 是不是新的问题？
- 我需要继续读吗？

#### 第二遍：抓取逻辑与细节 (Understanding / 1-2小时)

**目标**: 理解论文的核心内容和逻辑流，但忽略具体的数学证明或复杂的实验细节。

**核心方法：图像驱动深度理解（可选）**

根据用户在步骤 3 中的选择执行：

**如果用户选择"分析图像"**：
论文中的图表往往包含了最核心的信息。对于 PDF URL 解析的论文，使用以下流程系统化分析所有图像：

##### 2.1 获取论文备份路径

从 `parser.py` 的输出中获取论文目录路径：

```bash
cd ~/.claude/skills/paper-reader/scripts/

# 解析 PDF 并获取论文目录路径
RESULT=$(python3 parser.py "PDF_URL")
PAPER_DIR=$(echo "$RESULT" | jq -r '.paper_dir')
echo "论文目录: $PAPER_DIR"
```

**parser.py 输出格式**：
```json
{
  "markdown": "论文的 markdown 内容...",
  "images": ["图像文件路径列表"],
  "paper_dir": "/path/to/backup/{paper_id}"
}
```

##### 2.2 图像分析

使用 `analyze_images.py` 对论文目录中的图像进行分析：

```bash
# 使用 parser.py 输出的 paper_dir 路径
python3 analyze_images.py \
    --paper-dir "$PAPER_DIR" \
    --output "$PAPER_DIR/image_analysis.json"
```

**analyze_images.py 功能说明**：
- 自动解析论文目录，查找 `paper.md` 和 `images` 文件夹
- 从 markdown 内容中按顺序提取图像文件名，只保留实际存在的图像
- 自动定位每个图像在 markdown 中的上下文
- 使用 Kimi k2.5 进行多模态视觉分析
- 输出结构化的分析结果 JSON 文件

**输出格式**：
```json
{
  "total_images": 10,
  "analyzed_images": 8,
  "skipped_images": 2,
  "failed_images": 0,
  "results": [
    {
      "image_path": "...",
      "image_name": "figure1.jpg",
      "context_preview": "...",
      "context_found": true,
      "analysis": "### 图像类型识别\n...\n### 核心信息提取\n...",
      "progress": {
        "current": 1,
        "total": 10
      }
    }
  ]
}
```

**重要**: `analyze_images.py` 采用增量保存策略，每解析一个图像就立即将结果写入 JSON 文件。因此：
- 图像分析过程中，输出文件会不断更新
- 判断图像分析是否完成的方法：检查 `results` 数组中最后一个元素的 `progress.current` 是否等于 `total_images`
- 如果 `results[-1].progress.current == total_images`，说明所有图像都已解析完成

##### 2.3 图像分析框架

`analyze_images.py` 使用以下分析框架分析每个图像：

1. **图像类型识别**: 架构图、流程图、实验结果图、对比图、数据可视化等
2. **核心信息提取**:
   - 图表想要传达的关键结论
   - 坐标轴含义（X 轴和 Y 轴）
   - 对比图中最佳方法及提升幅度
3. **数据观察**:
   - 图中的趋势（上升、下降、收敛、波动等）
   - 显著的异常点或特殊情况
4. **与文字对应**:
   - 图中结论与上下文描述的一致性
   - 作者推论的合理性
5. **潜在问题**:
   - 图表误导性（如 Y 轴截断、刻度不合理等）
   - 误差线标注
   - 数据点密集度

##### 2.4 理解检查清单

完成所有图像分析后，检查是否能回答：

1. **方法理解**:
   - 论文提出的方法的核心架构是什么？（从架构图理解）
   - 各个模块之间的数据流如何交互？

2. **实验验证**:
   - 主要实验结果支持了哪些结论？
   - 与基线方法的对比优势在哪里？
   - 图表中的数据是否支撑作者声称的提升？

3. **关键洞察**:
   - 哪些图表最核心？为什么？
   - 是否有图表揭示了意外的发现？
   - 实验结果有什么局限性？

**输出**: 你应该能向别人简要介绍这篇论文的主旨、核心证据和初步优缺点。如果读不懂，可能需要补背景知识，或者该论文写得很烂。

**如果用户选择"跳过图像分析"**：
直接跳过上述图像分析步骤，继续进行以下文本理解检查：

##### 2.1 理解检查清单（无图像版本）

1. **问题理解**:
   - 论文标题、摘要和引言中定义了什么问题？
   - 作者声称的贡献是什么？

2. **方法理解**:
   - 从文字描述中理解方法的主要思路
   - 识别关键的创新点或技术方案

3. **实验验证**:
   - 主要实验结果支持了哪些结论？
   - 与基线方法的对比优势在哪里？
   - 实验设置和评估指标是什么？

4. **关键洞察**:
   - 最核心的发现是什么？
   - 实验结果有什么局限性？

**输出**: 你应该能向别人简要介绍这篇论文的主旨、核心证据和初步优缺点（仅基于文本内容）。

#### 第三遍：虚拟复现 (Deep Dive / 数小时至数天)

**目标**: 彻底掌握，达到可以审稿或基于此做研究的程度。

**核心技巧：虚拟重构 (Virtual Reimplementation)**

在看作者的解决方案之前，先自己想一遍解决方案：
- 假设你是作者，基于同样的已知条件，你会怎么设计实验？你会怎么证明？
- 将你的思路与作者的思路对比
  - 如果你想的和作者一样，说明你理解了
  - 如果不同，要么是作者极其高明（你学到了新东西），要么是作者有漏洞（你发现了切入点）

**输出**: 能够指出论文隐含的假设、实验的漏洞，并构思未来的工作方向

### 7. 进阶思考框架：沈向洋/华刚的"十个问题"

在精读（第三遍阅读）时，尝试回答以下问题：

**关于问题本身**:
1. **Input/Output**: 这篇文章主要讲了什么问题？输入和输出是什么？
2. **Novelty**: 这个问题以前有过吗？是一个全新的问题，还是旧问题的新解法？
3. **Importance**: 为什么这个问题现在依然重要？

**关于解决方案与相关工作**:
4. **Related Work**: 这个领域有哪些关键人物？有哪些相关研究？
5. **Solution**: 文章提出的核心解决方案是什么？（Key technical solution）
6. **Experiments**: 实验是如何设计的？设计得好吗？

**关于验证与评价**:
7. **Data**: 用了什么数据集？是否令人信服？
8. **Validation**: 实验结果是否强有力地支持了最初的假设？

**关于总结与展望**:
9. **Contribution**: 这篇文章真正的贡献是什么？（不同于作者自吹的贡献，是你客观认为的贡献）
10. **Next Step**: 下一步可以做什么？（这是挖掘自己课题的关键）

### 8. 博士生的四个段位 (Four Stages of Development)

时刻评估自己处于哪个阅读阶段：

**1. 消极阅读 (Passive Reading)**:
- **状态**: 像海绵一样被动吸收，只要是论文里写的就信以为真
- **对策**: 需要尽快脱离此阶段，即使是顶级期刊也可能存在偏见或错误

**2. 积极阅读 (Active Reading)**:
- **状态**: 开始思考"这些知识对我有什么用？"
- **动作**: 主动搜索相关文献，构建知识网络，搞清楚作者的意图

**3. 批判性阅读 (Critical Reading / Negative Thinking)**:
- **状态**: 像审稿人一样挑刺
- **特征**: 敢于挑战权威，寻找逻辑漏洞，问"Is this bullshit?"，这是科研思维成熟的标志

**4. 创造性阅读 (Creative Reading / Positive Thinking)**:
- **状态**: 在批判之后，能进行建设性的思考
- **特征**: 不仅发现别人的缺点，还能看到别人"失败"工作中的闪光点，将其转化为新的研究方向，这是学术大师的境界

### 9. 格式化输出

根据阅读目标调整输出详略。完整的论文阅读报告应包含以下内容：

```markdown
# 论文阅读报告

## 基本信息
- 标题：
- 作者：
- 发表年份/期刊/会议：
- 论文ID：{paper_id}（从 backup 目录获得）
- 备份路径：backup/{paper_id}/

## 一句话总结
[核心贡献的一句话概括]

## 5C评估
- **Category**: 论文的类别/领域
- **Context**: 研究背景和动机
- **Correctness**: 论文的正确性评估
- **Contribution**: 核心贡献点
- **Clarity**: 论文表述的清晰程度

**注意**: 以下"图表分析"部分仅在用户选择"分析图像"时才会生成。

## 图表分析
[从 image_analysis.json 整理的图像分析内容 - 如果选择了图像分析]

### Figure 1: [图表标题]
- **图像文件**: images/{filename}
- **图表类型**: [类型]
- **核心结论**: ...
- **数据观察**: ...
- **上下文对应**: ...
- **潜在问题**: ...

... （其他图表的分析）

## 沈向洋/华刚十个问题分析

### 关于问题本身
1. **Input/Output**: 输入是什么？输出是什么？
2. **Novelty**: 全新问题还是旧问题的新解法？
3. **Importance**: 为什么这个问题现在依然重要？

### 关于解决方案与相关工作
4. **Related Work**: 关键人物和相关研究
5. **Solution**: 核心技术方案
6. **Experiments**: 实验设计和质量

### 关于验证与评价
7. **Data**: 数据集选择和可信度
8. **Validation**: 实验结果对假设的支持力度

### 关于总结与展望
9. **Contribution**: 客观认定的贡献（非作者自吹）
10. **Next Step**: 潜在的后续工作方向

## 核心贡献
1. ...
2. ...
3. ...

## 关键假设
- ...

## 方法概述
[方法的主要思路和步骤]

## 实验验证
[主要实验设置和结果评估]

## 局限性
- ...

## 虚拟重构对比
如果我是作者，我会：[你的方案]
作者实际方案：[作者的方案]
差异分析：[对比结果和发现]

## 个人思考
- 当前阅读阶段：[消极/积极/批判性/创造性]
- 阅读启发
- 可能的改进方向
- 与自身工作的联系

## 引用建议
[如需引用时的关键引用句]
```

### 9.1 生成图像分析部分的说明（条件执行）

在生成论文阅读报告时，根据用户在步骤 3 中的选择执行：

**如果用户选择"分析图像"**：
1. **分析图像**：使用 `analyze_images.py --paper-dir backup/{paper_id} --output backup/{paper_id}/image_analysis.json` 分析所有图像
2. **等待完成**：必须等待所有图像解析完成才能继续生成报告。判断方法如下：
   - 读取 `backup/{paper_id}/image_analysis.json` 文件
   - 检查 `results` 数组中最后一个元素的 `progress.current` 是否等于 `total_images`
   - 如果 `results[-1].progress.current == total_images`，说明所有图像都已解析完成
   - 如果不满足条件，等待片刻后重新检查，直到所有图像解析完成
3. **读取结果**：解析 `backup/{paper_id}/image_analysis.json` 文件
4. **格式化输出**：将分析结果转换为报告中的"图表分析"部分

**如果用户选择"跳过图像分析"**：
1. 跳过上述步骤
2. 不在报告中生成"图表分析"部分
3. 生成报告中添加说明："注：本次阅读未包含图像分析"

## 阅读策略建议

### 精读 vs 泛读

- **精读**: 深度学习论文的立意、技巧、成果和思想，进行虚拟重构
- **泛读**: 快速浏览，了解研究问题和主要方法

> 深入阅读领域内最重要的10篇论文，胜过泛读500篇平庸的论文。

### 文献调研 (Literature Survey)
1. 利用 Google Scholar 找 3-5 篇最新论文
2. 读它们的"Related Work"部分，找到重合度最高的经典引用
3. 去顶级会议（如 CVPR, SIGCOMM, NeurIPS 等）的官网看最近几年的 Proceedings

### 笔记与复盘
读完后（特别是精读后），一定要写一段小结，最好做成 PPT 形式讲给别人听（费曼学习法），这是检验是否真懂的最好标准。

### 问题导向阅读

带着具体问题阅读：
- 这篇论文与我的研究有什么关系？
- 我能从中学到什么？
- 有什么可以借鉴的方法或思路？
- 有什么可以改进的地方？
- 如果我是作者，我会怎么做？

## 脚本工具说明

### parser.py
**功能**: PDF 解析和自动备份

**用法**:
```bash
python3 parser.py <PDF_URL> [OUTPUT_DIR]
```

**说明**:
- 解析 PDF 并自动在 `backup/{paper_id}/` 创建备份
- 可选：指定 OUTPUT_DIR 将内容同时复制到其他位置
- 避免重复解析：相同内容的 PDF 使用相同备份

### analyze_images.py
**功能**: 批量图像分析

**用法**:
```bash
python3 analyze_images.py \
    --paper-dir <PAPER_DIR> \
    --output <OUTPUT_JSON>
```

**参数**:
- `--paper-dir`: 论文目录路径（包含 paper.md 和 images 文件夹）
- `--output`: 输出 JSON 分析结果路径
- `--context-lines`: 上下文提取行数（默认：50）

**功能说明**:
- 自动解析论文目录结构，查找 paper.md 和 images 文件夹
- 支持嵌套的 images/images/ 目录结构
- 从 markdown 按顺序提取图像文件名，只分析实际存在的图像
- 自动定位图像上下文并调用 Kimi k2.5 进行多模态分析
- 增量保存结果，每分析一个图像就更新 JSON 文件

---

**核心理念总结**: 博士读论文的本质不是"学习知识"，而是"训练思维"和"寻找机会"。请遵循：**扫读筛选 → 选择是否分析图像 → 带着十个问题精读 → (可选) 图像分析 → 虚拟重构 → 寻找创新点** 的路径。
