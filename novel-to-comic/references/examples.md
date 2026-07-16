# Example Workflows

## 示例1: 从 URL 生成漫画

**用户输入:**
```
帮我生成这本小说的本章漫画: https://example.com/novel/chapter-1.html
风格用中国漫画
```

**工作流:**
1. 用 scripts/novel_to_comic.py 的 extract_text_from_url() 获取章节文本
2. 分析文本: 小说名"星辰变", 章节"第一章 觉醒"
3. 分解6个场景:
   - Scene 1: 主角秦羽在海底修炼
   - Scene 2: 发现神秘星辰碎片
   - Scene 3: 碎片融入体内产生剧痛
   - Scene 4: 获得星辰之力, 突破境界
   - Scene 5: 引发天地异象
   - Scene 6: 神秘人物出现注视主角
4. 确定风格: 中国漫画(Manhua)
5. 生成6张图片, 保存到 novel-to-comic-output/星辰变/第一章-觉醒/
6. 向用户报告结果

## 示例2: 从纯文本生成

**用户输入:**
```
以下是我的小说章节内容, 帮我生成漫画:
[长篇章节文字]
```
**工作流:**
1. 直接使用用户提供的文字
2. 分析、分解场景(默认4~8个)
3. 默认中国漫画风格
4. 按场景顺序生成图片

## 示例3: 连续章节(保持角色一致性)

**用户输入(第二次):**
```
继续上一章的漫画, 下一章内容:
[下一章文字]
```
**工作流:**
1. 检查 novel-to-comic-output/[小说名]/characters.json
2. 存在则加载角色描述
3. 分析新章节, 已有角色不需重新描述
4. 生成新章节漫画
5. 更新 characters.json(添加新角色或已有角色变化)

## 文件结构示例

```
novel-to-comic-output/
  - 星辰变/
    - characters.json
    - 第一章-觉醒/
      - scene-01-海底修炼.png
      - scene-02-发现星辰碎片.png
      - scene-03-碎片融入体内.png
      - scene-04-获得星辰之力.png
      - scene-05-天地异象.png
      - scene-06-神秘人物注视.png
    - 第二章-风波/
      - scene-01-...png
  - 斗破苍穹/
    - characters.json
    - 第一章-陨落的天才/
      - ...
```
