---
name: novel-to-comic
description: This skill should be used when the user asks to convert a novel, chapter, fiction scene, local text file, or story URL into comics, manga, manhua, manhwa, webtoon, or storyboard images, including requests such as “小说转漫画”“把这一章做成漫画”或“生成连续剧情漫画”.
---

# Novel to Comic（小说转漫画）

将小说章节拆分为连续场景，并使用 Cursor 的 `GenerateImage` 生成漫画图片。

## 默认值

- 风格：中国漫画（Manhua）
- 场景数：4～8
- 比例：竖版 `3:4`
- 文字：默认不在图片中生成文字
- 输出根目录：`novel-to-comic-output/`

## 工作流

### 1. 获取正文

按输入类型选择工具：

- 章节 URL：先使用 `WebFetch` 获取正文。
- 本地文本文件：使用 `ReadFile`。
- 用户直接粘贴的内容：直接分析。

仅当 `WebFetch` 失败时，使用 `Shell` 执行：

```shell
python novel-to-comic/scripts/novel_to_comic.py --url "<URL>" --text-output "novel-to-comic-output/extracted-chapter-<时间戳>.txt"
```

然后使用 `ReadFile` 读取命令中传给 `--text-output` 的同一个时间戳文件。终端中的 200 字仅为预览，不可作为章节分析输入。

可选依赖缺失时，先告知用户，再按需执行：

```shell
python -m pip install -r novel-to-comic/requirements.txt
```

登录页、验证码、付费墙或反爬限制无法绕过时，说明原因并请用户提供正文。不得虚构未获取到的内容。

### 2. 分析章节

输出供用户确认的结构化方案：

1. 小说名称
2. 章节标题或编号
3. 角色卡：姓名、年龄感、体型、发型发色、五官、服装、标志物、气质
4. 4～8 个关键场景，每个场景包含：
   - 场景摘要
   - 出场角色
   - 动作与表情
   - 环境与时间
   - 构图与景别
   - 光线、色调与情绪

缺少小说名或章节名时，只询问无法可靠推断的字段。生成图片前必须让用户确认场景划分、风格、比例和数量。

### 3. 准备输出与角色资料

使用脚本创建目录：

```shell
python novel-to-comic/scripts/novel_to_comic.py --create-dir --novel "<小说名>" --chapter "<章节名>"
```

目标结构：

```text
novel-to-comic-output/
  <小说名>/
    characters.json
    <章节名>/
      scene-01-<描述>.png
```

连续章节生成前使用 `ReadFile` 加载 `characters.json`。新增角色或外观发生剧情性变化时，使用 `ApplyPatch` 创建或更新合法 JSON；不得无原因改变已有角色设定，也不得覆盖无法解析的旧文件。

使用以下结构持久化角色与基准图：

```json
{
  "schema_version": 1,
  "characters": {
    "林轩": {
      "appearance": "约20岁，利落黑色短发，窄脸，深邃黑眸",
      "clothing": "青色交领长袍，深色腰封，腰佩旧银长剑",
      "temperament": "冷峻克制",
      "reference_images": ["novel-to-comic-output/小说名/角色基准/scene-01-林轩.png"],
      "current_changes": ["右肩受伤"]
    }
  }
}
```

跨章节优先读取 `reference_images`，不得从文件名猜测角色身份。

生成 `1:1` 角色基准图后，使用相同归档命令并将章节名设为 `角色基准`：

```shell
python novel-to-comic/scripts/novel_to_comic.py --place-image "<基准图实际路径>" --novel "<小说名>" --chapter "角色基准" --scene 1 --description "<角色名>"
```

把脚本返回的归档路径写入该角色的 `reference_images`。

### 4. 生成图片

用户要求小说转漫画即构成明确的图片生成请求。每个场景调用一次 `GenerateImage`：

- `description`：按 `references/prompting.md` 组织完整画面描述。
- `filename`：使用 `scene-NN-简短描述.png`，不得包含目录。
- `aspect_ratio`：
  - 竖版单页：`3:4`
  - 横版单页：`4:3`
  - 宽屏场景：`16:9`
  - 条漫：`9:16`
- `reference_image_paths`：从第二个相关场景开始，传入最能代表角色外观的已生成图片。

`reference_image_paths` 必须是路径数组，例如：

```json
["path/to/lin-xuan-reference.png", "path/to/su-xiaoxiao-reference.png"]
```

重要角色首次出场时，优先生成或选择一张脸部清晰、无遮挡、服装完整的基准图。多人场景为每个主要角色各传入一张正确基准图，并在 `description` 中说明姓名与站位；不得使用外观错误的图片继续传播。

默认每张图都加入：`no text, no speech bubbles, no captions, no letters, no watermark`。用户明确要求画面文字时，按用户要求生成，不再加入冲突约束。

每场景一张独立图片，不要求模型生成多格拼接。超过 4 个场景时分批生成，每批 2 张，批次之间核对角色外观。

`GenerateImage` 返回路径后，将图片复制到目标章节目录：

```shell
python novel-to-comic/scripts/novel_to_comic.py --place-image "<实际生成路径>" --novel "<小说名>" --chapter "<章节名>" --scene 1 --description "<简短描述>"
```

只有脚本报告 `[OK] Archived generated image` 后，才能把目标路径作为交付路径。原始生成文件保留。

归档目标已存在时，脚本会覆盖同名目标；只允许在用户确认重试或明确替换该场景时使用相同场景编号。

### 5. 失败恢复

- 单张失败：保留成功图片，仅重试失败场景；同一场景自动调整后最多重试 1 次。
- 角色外观漂移：使用正确图片作为参考图，并在描述中重申固定特征。
- 图片出现乱码文字：重试并加强无文字约束。
- 内容安全限制：说明受限场景，提供不改变剧情核心的安全构图方案。
- 参数错误、文件路径失效或参考图不存在：修正参数后重试，不沿用无效路径。

### 6. 最终交付

报告：

1. 小说名称与章节
2. 计划场景数、成功数和失败数
3. 每张图片的实际保存路径
4. 角色资料文件路径
5. 可选下一步：重试失败场景、调整画风或继续下一章

## 参考资源

- `references/prompting.md`：`GenerateImage` 提示词与角色一致性
- `references/examples.md`：URL、文本、连续章节和失败恢复示例
