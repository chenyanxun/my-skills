---
name: novel-to-comic
description: Use when the user wants to generate comic/manga-style images from novel chapter content. The user provides either a chapter URL or chapter text, and this skill guides the process of parsing the chapter into scenes/panels, generating comic-style images for each scene, and organizing output as novel-name -> chapter -> images. Includes scripts for scene extraction and directory management, plus reference materials for comic-style prompting and character consistency.
---

# Novel to Comic(小说转漫画)

将小说章节内容转化为漫画图片。接收用户提供的小说章节链接或章节文字，按 **小说名称 -> 章节 -> 图片** 的目录结构输出。

## 工作流程

`
输入: 章节链接 / 章节文字 -> 解析章节 -> 提取场景 -> 生成漫画图片 -> 按小说名/章节/图片 存放
`

使用此技能时，按照以下步骤顺序执行:

## Step 1: 确定输入来源

- 如果用户提供的是 **URL(链接)**: 使用 Python requests/httpx 获取页面，优先用 readability-lxml 或 newspaper3k 提取正文，避免广告等噪音
- 如果用户提供的是 **纯文字内容**: 直接作为章节内容使用
- 获取失败时要求用户直接提供章节文字

## Step 2: 分析章节

用 LLM 能力分析章节文本，提取以下信息:
1. **小说名称** - 从章节中推断，或询问用户
2. **章节标题/编号** - 例如"第一章 觉醒"
3. **关键场景列表**(4~8个): 每个含场景描述、涉及角色、环境/背景、对话、情绪/氛围
4. **角色描述**: 首次出场角色的外貌、服装、气质

告知用户分析结果，确认后继续。用户可调整场景划分。

## Step 3: 确定漫画风格

询问用户偏好风格(默认中国漫画Manhua):

| 风格 | Prompt 关键词 |
|------|--------------|
| 日式漫画(Manga) | manga style, black and white, screentone, crosshatch |
| 中国漫画(Manhua) | Chinese manhua style, full color, detailed lineart |
| 韩国漫画(Manhwa) | webtoon style, Korean manhwa, soft rendering |
| 美式漫画 | American comic style, bold outlines, vibrant colors |
| 水墨风 | Chinese ink wash painting, brush strokes |
| 绘本风 | picture book style, soft watercolor |

## Step 4: 生成漫画图片

每个场景用内置 image_gen 工具生成漫画风格图片。

### Prompt 结构

`
Use case: illustration-story
Style/medium: [选定风格关键词]
Primary request: [场景描述]
Subject: [角色外貌、服装、表情、动作]
Scene/backdrop: [环境背景]
Composition/framing: [远景/中景/特写等]
Lighting/mood: [光线和氛围]
Text: ""
Constraints: no text, no speech bubbles, no captions, no letters, no watermark
`

### 关键约束

- **角色一致性**: 同一角色的外貌、服装、发色、体型在连续场景中保持一致
- **无文字**: 所有 prompt 必须加 "no text, no speech bubbles, no captions, no letters"
- **图片尺寸**:
  - 竖版单页: 1024x1536
  - 横版单页: 1536x1024
  - 条漫/webtoon: 1024x2048
- **每场景一张独立图片**, 不做多格拼接
- 场景多时(>4)分批生成，每批2张

## Step 5: 组织输出

按以下结构保存:

`
小说名称/
  - 章节标题/
    - scene-01-描述.png
    - scene-02-描述.png
`

创建目录和文件名:
- 用 scripts/novel_to_comic.py 的 create_output_dir() 创建目录
- 文件名用 generate_scene_filename() 生成
- 输出基础目录用 novel-to-comic-output/

### 最终交付

生成完成后向用户报告:
1. 小说名称和章节
2. 生成场景总数
3. 每张图片的保存路径
4. 建议下一步(调整场景、生成更多章节等)

## 角色一致性管理

- **首次出场记录**: 角色第一次出现时生成详细外貌描述并保存
- **跨章传递**: 连续生成多章时传递角色描述
- **存储文件**: novel-to-comic-output/[小说名]/characters.json

## 参考资源

- references/prompting.md: prompt 模板和最佳实践
- references/examples.md: 完整工作流示例
