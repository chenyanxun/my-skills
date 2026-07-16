# Cursor GenerateImage 提示词指南

## 工具参数

```text
description: 画面主体、动作、环境、构图、风格、色调、光线、情绪和约束
filename: scene-01-简短描述.png
reference_image_paths: ["角色A基准图路径", "角色B基准图路径"]
aspect_ratio: 1:1 | 3:4 | 4:3 | 16:9 | 9:16
```

`filename` 只写文件名，不包含目录。工具返回的路径才是实际保存路径。

## Description 模板

```text
Create a single comic illustration, not a multi-panel page.
Style: [漫画风格及媒介]
Story moment: [本场景发生的关键事件]
Characters: [每个角色的固定外貌、服装、表情和动作]
Environment: [地点、时代、天气、时间和关键道具]
Composition: [景别、视角、主体位置、动作方向和空间关系]
Lighting and mood: [光线、色调、情绪]
Continuity: [与上一场景保持一致的特征]
Constraints: no text, no speech bubbles, no captions, no letters, no watermark
```

描述具体可见的瞬间，不把整段剧情、心理解释或多个时间点塞入一张图。

## 角色卡

每个角色固定记录：

```text
[角色名]｜[年龄感/性别表现/体型]｜[脸型与五官]｜[发型发色]
｜[固定服装与颜色]｜[标志物]｜[气质]｜[当前剧情变化]
```

示例：

```text
林轩｜约20岁男性、中等偏瘦｜窄脸、深邃黑眸｜利落黑色短发
｜青色交领长袍、深色腰封｜腰佩旧银长剑｜冷峻克制｜右肩有新伤
```

## 一致性策略

1. 第一张角色清晰出现的图片使用完整角色卡。
2. 后续场景继续写固定特征，不能只写角色姓名。
3. 将最清晰、最准确的已生成角色图以路径数组传入 `reference_image_paths`。
4. 重要角色优先使用脸部清晰、无遮挡、服装完整的基准图；必要时先用 `1:1` 生成角色基准图。
5. 多人场景为每个主要角色提供一张基准图，并分别说明站位、身高差、服装颜色和动作。
6. 剧情导致换装、受伤或年龄变化时，更新 `characters.json` 的变化字段。
7. 参考图本身有错误时不得继续传播，改用更早的正确图片。

## 风格关键词

- 日式漫画：`Japanese manga, black and white, screentone, crosshatching, expressive linework`
- 中国漫画：`Chinese manhua, full-color digital painting, detailed line art, cinematic fantasy lighting`
- 韩国条漫：`Korean manhwa, webtoon illustration, clean line art, soft rendering, dramatic lighting`
- 美式漫画：`American comic book art, bold ink outlines, dynamic anatomy, vivid colors`
- 水墨风：`Chinese ink wash painting, expressive brushwork, flowing ink, poetic negative space`
- 绘本风：`storybook illustration, soft watercolor, gentle shapes, warm paper texture`

## 构图选择

- 战斗：中景或全景、倾斜视角、明确动作方向
- 对话：中景或过肩镜头、突出双方空间关系
- 情绪：面部特写、浅景深、克制背景
- 环境建立：远景、人物比例较小、突出地点规模
- 登场：中全景、低机位、轮廓光
- 悬念：局部特写、遮挡构图、低调照明
- 离别：远景或背影、留白、冷暖色分离

## 常见修正

- 角色漂移：重复固定特征并增加正确参考图。
- 多手多指：简化手部动作，避免多人手部交叠。
- 错误文字：加强无文字约束并移除画面中的招牌、书页等文字载体。
- 场景拥挤：减少背景人物和无关道具，只保留叙事必需元素。
