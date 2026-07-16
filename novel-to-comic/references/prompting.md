# Comic-Style Prompting Guide

## Prompt 结构模板

`
Use case: illustration-story
Asset type: comic/manga panel
Primary request: [场景描述]
Style/medium: [选定漫画风格关键词]
Scene/backdrop: [环境背景]
Subject: [角色外貌、服装、动作、表情]
Composition/framing: [远景/中景/特写等]
Lighting/mood: [光线和氛围]
Color palette: [色调]
Text: ""
Constraints: no text, no speech bubbles, no captions, no letters, no watermark
`

## 角色一致性策略

### 角色描述模板

`
[角色名] - [年龄/性别/体型] - [发型/发色] - [眼睛特征] - [服装] - [气质]
`

示例:
- 林轩 - 20岁男性 - 中等身材 - 黑色短发 - 深邃黑眸 - 青色长袍/腰佩长剑 - 冷峻
- 苏小小 - 18岁女性 - 娇小 - 及腰黑发/红色发带 - 水灵杏眼 - 浅粉襦裙 - 活泼

### 跨场景传递

1. 第一个场景写完整角色描述
2. 后续场景只需写差异(服装变化、受伤等)
3. 优先用 characters.json 中的描述

## 不同风格关键词

### 日式漫画(Manga)
- manga style, Japanese comic art
- black and white, screentone textures, crosshatch
- dynamic lines, expressive eyes
- tonal gradation, halftone dots

### 中国漫画(Manhua)
- Chinese manhua style, full color digital painting
- detailed lineart, vibrant colors
- beautiful character designs, fantasy setting
- smooth rendering, soft lighting

### 韩国漫画(Manhwa/Webtoon)
- Korean webtoon style, digital art
- soft rendering, pastel tones, glowing effects
- beautiful faces, slender proportions
- dramatic lighting, sparkle effects

### 水墨风
- Chinese ink wash painting style, shui mo hua
- brush strokes, flowing ink, negative space
- minimalist, poetic atmosphere

## 场景构图建议

| 场景类型 | 推荐构图 | 说明 |
|---------|---------|------|
| 战斗/对决 | 中景+动态角度 | 展示动作和双方位置 |
| 对话/交谈 | 中景+过肩镜头 | 展示表情和氛围 |
| 情感/感动 | 特写+柔光 | 突出面部表情 |
| 环境/风景 | 远景+宽幅 | 展示宏大场景 |
| 登场/亮相 | 中全景+仰视 | 突出气势 |
| 内心/独白 | 特写+侧光 | 突出内心活动 |
| 悬念/紧张 | 特写+暗调 | 加强紧张感 |
| 离别/分别 | 远景+背影 | 营造离别感 |
