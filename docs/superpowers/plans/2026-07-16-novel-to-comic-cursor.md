# Novel to Comic Cursor Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 `novel-to-comic` 改造成使用 Cursor 实际工具、具备可靠辅助脚本和自动化测试的项目内 Skill。

**Architecture:** Cursor 负责内容读取、章节分析、用户确认与图片生成；Python 辅助脚本只负责确定性的网页文本兜底、Windows 安全路径和角色资料持久化。Skill 通过精简的 `SKILL.md` 编排流程，并按需读取提示词和示例参考。

**Tech Stack:** Cursor Agent Skills、Markdown/YAML、Python 3.10+ 标准库、`unittest`，可选 `requests`、`readability-lxml`、`newspaper3k`

## Global Constraints

- 保留 `novel-to-comic/` 当前目录，不复制到用户目录或 `.cursor/skills/`。
- 图片生成只使用 Cursor 的 `GenerateImage`，比例仅使用 `3:4`、`4:3`、`16:9`、`9:16`。
- URL 内容优先通过 `WebFetch` 获取，Python 仅作为失败后的兜底。
- 不自动绕过登录、验证码或反爬限制。
- 不实现图像后处理或多格漫画拼接。
- 当前目录不是 Git 仓库；不得初始化仓库或创建提交。

---

## 文件结构

- 修改 `novel-to-comic/SKILL.md`：Cursor 原生工作流及工具边界。
- 修改 `novel-to-comic/references/prompting.md`：`GenerateImage` 描述和参考图策略。
- 修改 `novel-to-comic/references/examples.md`：覆盖 Cursor 执行及失败恢复。
- 修改 `novel-to-comic/scripts/novel_to_comic.py`：安全路径、角色校验和 URL 诊断。
- 创建 `novel-to-comic/tests/test_novel_to_comic.py`：辅助脚本回归测试。
- 删除 `novel-to-comic/agents/openai.yaml`：移除非 Cursor 元数据。

### Task 1：建立辅助脚本的回归测试与安全数据接口

**Files:**
- Create: `novel-to-comic/tests/test_novel_to_comic.py`
- Modify: `novel-to-comic/scripts/novel_to_comic.py`

**Interfaces:**
- 保留：`create_output_dir(novel_name, chapter_title, base_dir=None) -> Path`
- 保留：`load_characters(novel_dir) -> dict[str, dict[str, str]]`
- 保留：`save_characters(novel_dir, characters) -> None`
- 保留：`generate_scene_filename(scene_num, description, ext=".png") -> str`
- 新增：`CharacterDataError(ValueError)`
- `_sanitize(name: object) -> str` 必须生成 Windows 安全名称。

- [ ] **Step 1：创建测试模块并写失败测试**

```python
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "novel_to_comic.py"
SPEC = importlib.util.spec_from_file_location("novel_to_comic", SCRIPT)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class PathTests(unittest.TestCase):
    def test_sanitize_windows_reserved_name(self):
        self.assertEqual(module._sanitize("CON"), "CON_")

    def test_sanitize_removes_trailing_dots_and_spaces(self):
        self.assertEqual(module._sanitize("chapter. "), "chapter")

    def test_scene_filename_normalizes_extension(self):
        self.assertEqual(
            module.generate_scene_filename(3, "觉醒", "jpg"),
            "scene-03-觉醒.jpg",
        )


class CharacterTests(unittest.TestCase):
    def test_round_trip_characters(self):
        with tempfile.TemporaryDirectory() as tmp:
            expected = {"林轩": {"appearance": "黑色短发", "clothing": "青色长袍"}}
            module.save_characters(tmp, expected)
            self.assertEqual(module.load_characters(tmp), expected)

    def test_invalid_json_is_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "characters.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaisesRegex(module.CharacterDataError, "characters.json"):
                module.load_characters(tmp)

    def test_rejects_non_mapping_character_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(module.CharacterDataError):
                module.save_characters(tmp, ["not", "a", "mapping"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2：运行测试并确认预期失败**

Run: `python -m unittest discover -s novel-to-comic/tests -v`

Expected: `ERROR` 或 `FAIL`，原因包括缺少 `CharacterDataError`、保留名称未处理和扩展名未规范化。

- [ ] **Step 3：实现最小安全路径与角色校验**

在脚本中增加：

```python
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class CharacterDataError(ValueError):
    """Raised when characters.json cannot be safely read or written."""


def _validate_characters(characters):
    if not isinstance(characters, dict):
        raise CharacterDataError("Character data must be a JSON object")
    return characters
```

更新 `_sanitize()`：替换非法字符、去除尾随点和空格、处理 Windows 保留名称。更新角色读写函数：捕获 `json.JSONDecodeError` 并转换为包含文件路径的 `CharacterDataError`，写入前调用 `_validate_characters()`。更新扩展名处理：

```python
if not ext.startswith("."):
    ext = f".{ext}"
```

- [ ] **Step 4：运行测试并确认通过**

Run: `python -m unittest discover -s novel-to-comic/tests -v`

Expected: 6 tests，全部 `ok`。

### Task 2：为 URL 兜底提取增加可测试解析和明确诊断

**Files:**
- Modify: `novel-to-comic/tests/test_novel_to_comic.py`
- Modify: `novel-to-comic/scripts/novel_to_comic.py`

**Interfaces:**
- 保留：`extract_text_from_url(url) -> str | None`
- 新增：`ExtractionResult(text: str | None, attempts: tuple[str, ...])`
- 新增：`extract_text_from_url_with_diagnostics(url) -> ExtractionResult`
- 新增：`_extract_text_from_html(source: str) -> str | None`

- [ ] **Step 1：增加 HTML 解析、URL 校验和诊断失败测试**

```python
class ExtractionTests(unittest.TestCase):
    def test_extracts_common_chapter_container(self):
        html = '<div id="content"><p>第一段。</p><p>第二段。</p></div>'
        self.assertEqual(module._extract_text_from_html(html), "第一段。第二段。")

    def test_rejects_non_http_url(self):
        with self.assertRaisesRegex(ValueError, "http"):
            module.extract_text_from_url_with_diagnostics("file:///secret.txt")

    def test_diagnostics_result_records_attempts(self):
        result = module.ExtractionResult(None, ("readability-lxml: unavailable",))
        self.assertIsNone(result.text)
        self.assertIn("unavailable", result.attempts[0])
```

- [ ] **Step 2：运行测试并确认预期失败**

Run: `python -m unittest discover -s novel-to-comic/tests -p "test_novel_to_comic.py" -v`

Expected: `ERROR`，缺少 `ExtractionResult`、`_extract_text_from_html` 和诊断函数。

- [ ] **Step 3：实现纯 HTML 解析器和诊断结果**

```python
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ExtractionResult:
    text: str | None
    attempts: tuple[str, ...]


def _validate_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must use http or https")
```

将通用容器解析提取到 `_extract_text_from_html()`。在 `extract_text_from_url_with_diagnostics()` 中依次尝试 readability、newspaper 和基础 HTML，给每次失败记录依赖缺失或异常类型；兼容包装函数只返回 `.text`：

```python
def extract_text_from_url(url):
    return extract_text_from_url_with_diagnostics(url).text
```

- [ ] **Step 4：让 CLI 输出诊断并保持非零退出状态**

当 `--url` 提取失败时，逐行输出 `attempts` 到标准错误并 `return 1`；成功时 `return 0`，入口使用：

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5：运行全部测试**

Run: `python -m unittest discover -s novel-to-comic/tests -v`

Expected: 9 tests，全部 `ok`。

### Task 3：重写 Skill 为 Cursor 原生工作流

**Files:**
- Modify: `novel-to-comic/SKILL.md`
- Modify: `novel-to-comic/references/prompting.md`
- Modify: `novel-to-comic/references/examples.md`
- Delete: `novel-to-comic/agents/openai.yaml`

**Interfaces:**
- Skill 自动触发：用户要求把小说、章节、故事文本或章节 URL 转为漫画图片。
- Cursor 工具：`WebFetch`、`ReadFile`、`GenerateImage`、`Shell`。
- 输出：`novel-to-comic-output/<小说名>/<章节名>/scene-NN-描述.png`。

- [ ] **Step 1：记录当前 Skill 的基线缺陷**

用以下检查作为 RED：

Run: `rg -n "image_gen|1024x1536|1536x1024|1024x2048|requests/httpx|agents/openai" novel-to-comic`

Expected: 找到旧工具名、Cursor 不支持的固定尺寸、脚本优先抓取描述或 OpenAI 元数据。

- [ ] **Step 2：重写 `SKILL.md`**

Frontmatter 使用：

```yaml
---
name: novel-to-comic
description: Converts novel chapters, story text, local text files, or chapter URLs into a sequence of comic-style images. Use when the user asks to turn a novel, chapter, fiction scene, or story URL into comics, manga, manhua, manhwa, webtoon, or storyboard images.
---
```

正文必须包含：

1. 输入路由：URL 使用 `WebFetch`；本地文件使用 `ReadFile`；直接文本直接分析。
2. `WebFetch` 失败后才通过 `Shell` 执行 `python novel-to-comic/scripts/novel_to_comic.py --url "<URL>"`。
3. 分析输出固定字段：小说名、章节名、角色卡、4 至 8 个场景。
4. 用户确认场景和风格后才调用 `GenerateImage`。
5. 比例映射：竖版 `3:4`、横版 `4:3`、宽屏 `16:9`、条漫 `9:16`。
6. 每个场景调用一次 `GenerateImage`，设置明确文件名；不得声称工具支持固定像素尺寸。
7. 后续图片将已生成的角色参考图放入 `reference_image_paths`。
8. 单张失败时保留成功图片、报告失败场景并仅重试失败项。
9. 最终报告小说、章节、成功/失败数量和路径。

- [ ] **Step 3：更新提示词参考**

使用与 `GenerateImage` 参数一致的说明：

```text
description: 具体描述主体、构图、风格、颜色、文字约束和角色固定特征
filename: scene-01-场景描述.png
reference_image_paths: 从第二个相关场景开始传入已生成的角色参考图
aspect_ratio: 3:4 | 4:3 | 16:9 | 9:16
```

强调 `description` 中加入 `no text, no speech bubbles, no captions, no letters, no watermark`，但用户明确要求画面文字时应服从用户要求。

- [ ] **Step 4：更新执行示例**

写出四个完整例子：URL 输入、本地/直接文本、连续章节角色继承、网页或单图失败恢复。每个例子都明确 Cursor 工具调用顺序及输出目录。

- [ ] **Step 5：删除 OpenAI 专用元数据**

删除 `novel-to-comic/agents/openai.yaml`；若空的 `agents/` 目录仍存在，无需保留。

- [ ] **Step 6：运行静态 RED→GREEN 检查**

Run: `rg -n "image_gen|1024x1536|1536x1024|1024x2048|requests/httpx|agents/openai" novel-to-comic`

Expected: 无匹配。

Run: `rg -n "GenerateImage|WebFetch|reference_image_paths|aspect_ratio" novel-to-comic/SKILL.md novel-to-comic/references`

Expected: 四个 Cursor 关键术语均有匹配。

### Task 4：最终验证 Skill 和辅助脚本

**Files:**
- Verify: `novel-to-comic/SKILL.md`
- Verify: `novel-to-comic/references/*.md`
- Verify: `novel-to-comic/scripts/novel_to_comic.py`
- Verify: `novel-to-comic/tests/test_novel_to_comic.py`

- [ ] **Step 1：运行 Python 回归测试**

Run: `python -m unittest discover -s novel-to-comic/tests -v`

Expected: 全部测试通过，无 traceback。

- [ ] **Step 2：运行目录创建冒烟测试**

Run: `python novel-to-comic/scripts/novel_to_comic.py --create-dir --novel "测试:小说" --chapter "CON" --output novel-to-comic-output/smoke-test`

Expected: 退出码 0，路径包含 `测试_小说/CON_`。

- [ ] **Step 3：检查 Skill 结构与大小**

Run: `python -c "from pathlib import Path; p=Path('novel-to-comic/SKILL.md'); print(len(p.read_text(encoding='utf-8').splitlines()))"`

Expected: 小于 500 行。

Run: `python -c "from pathlib import Path; p=Path('novel-to-comic/SKILL.md'); t=p.read_text(encoding='utf-8'); assert t.startswith('---\\nname: novel-to-comic\\n'); assert 'description:' in t; print('OK')"`

Expected: `OK`。

- [ ] **Step 4：检查引用和遗留内容**

Run: `rg -n "references/(prompting|examples)\\.md" novel-to-comic/SKILL.md`

Expected: 两个参考文件均被引用。

Run: `rg -n "image_gen|1024x1536|1536x1024|1024x2048|openai.yaml" novel-to-comic`

Expected: 无匹配。

- [ ] **Step 5：清理冒烟测试输出**

删除 `novel-to-comic-output/smoke-test/`，仅删除本计划创建的测试目录，不影响已有输出。

- [ ] **Step 6：汇总交付**

报告修改文件、删除文件、测试数量和命令结果；明确 Skill 保持在项目的 `novel-to-comic/` 中，未写入任何用户目录。
