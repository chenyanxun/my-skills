# Cursor 执行示例

## 示例 1：章节 URL

用户：

```text
把这个章节做成中国漫画，竖版：https://example.com/chapter-1
```

执行顺序：

1. 使用 `WebFetch` 获取章节正文。
2. 若失败，执行：

   ```shell
   python novel-to-comic/scripts/novel_to_comic.py --url "https://example.com/chapter-1" --text-output "novel-to-comic-output/extracted-chapter-20260716-103000.txt"
   ```

3. 使用 `ReadFile` 读取 `--text-output` 指定的同一个时间戳文件，不能只分析终端预览。
4. 分析小说名、章节名、角色卡和 4～8 个场景。
5. 将场景方案展示给用户确认。
6. 创建章节目录。
7. 每个场景调用一次 `GenerateImage`，使用 `aspect_ratio: "3:4"`。
8. 第二张开始用数组形式在 `reference_image_paths` 中传入正确的角色参考图。
9. 使用 `--place-image` 把每张成功图片复制到章节目录。
10. 报告归档后的真实图片路径。

## 示例 2：直接粘贴正文

用户：

```text
以下是第三章内容，请做成 6 张韩国条漫：
[章节正文]
```

执行顺序：

1. 直接分析正文，不再调用网页工具。
2. 无法推断小说名时只询问小说名。
3. 输出 6 个场景和角色卡供确认。
4. 确认后使用韩国条漫风格和 `aspect_ratio: "9:16"`。
5. 分三批生成，每批 2 张；每批后核对服装、发色和标志物。
6. 每张生成成功后使用 `--place-image` 归档，并以归档路径交付。

## 示例 3：本地文本文件

用户：

```text
把 @chapters/第十章.txt 做成日式黑白漫画。
```

执行顺序：

1. 使用 `ReadFile` 读取文件。
2. 分析并确认场景。
3. 使用日式黑白漫画描述和用户指定比例；未指定时使用 `3:4`。
4. 使用 `scene-01-*.png` 等文件名调用 `GenerateImage`。
5. 每张生成成功后使用 `--place-image` 归档，并以归档路径交付。

## 示例 4：连续章节

用户：

```text
继续上一章，这是下一章正文：
[正文]
```

执行顺序：

1. 从 `novel-to-comic-output/<小说名>/characters.json` 加载已有角色卡。
2. 只为新角色补充角色卡；已有角色沿用固定特征。
3. 若剧情中出现受伤或换装，记录为当前变化，不覆盖基础外观。
4. 使用 `ReadFile` 加载角色资料，并用 `ApplyPatch` 更新合法 JSON。
5. 将上一章每个主要角色最准确的基准图组成 `reference_image_paths` 数组。
6. 完成后更新角色资料。

## 示例 5：失败恢复

若 6 张图片中第 4 张失败：

1. 保留第 1～3、5～6 张，不重新生成。
2. 报告第 4 个场景失败及工具返回的原因。
3. 简化第 4 个场景描述或提供安全构图方案。
4. 用户确认后仅重试第 4 张。

若第 3 张角色发色错误：

1. 不把第 3 张作为后续参考图。
2. 选用第 1 或第 2 张正确图片。
3. 在重试描述中明确固定发色、发型和服装颜色。

## 输出示例

```text
novel-to-comic-output/
  星辰变/
    characters.json
    第一章-觉醒/
      scene-01-海底修炼.png
      scene-02-发现星辰碎片.png
      scene-03-碎片融入体内.png
```

最终交付以 `--place-image` 成功后报告的章节目录路径为准；未归档成功时才报告 `GenerateImage` 原始路径，并明确标记为“未归档”。
