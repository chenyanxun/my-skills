#!/usr/bin/env python3
"""
Novel to Comic - Helper script for novel-to-comic skill.

Functions:
- create_output_dir(novel_name, chapter_title, base_dir): Create dir structure
- extract_text_from_url(url): Extract chapter text from URL
- load_characters(novel_dir): Load saved character descriptions
- save_characters(novel_dir, characters): Save character descriptions
- generate_scene_filename(scene_num, description, ext): Generate image filename
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


class CharacterDataError(ValueError):
    """Raised when characters.json contains invalid character data."""


@dataclass(frozen=True)
class ExtractionResult:
    """Text extraction outcome together with attempted strategies."""

    text: str | None
    attempts: tuple[str, ...]


def create_output_dir(novel_name, chapter_title, base_dir=None):
    """Create output directory structure for a novel chapter.

    Args:
        novel_name: Name of the novel (used as directory name)
        chapter_title: Chapter title or number (used as subdirectory name)
        base_dir: Base output directory (default: ./novel-to-comic-output/)

    Returns:
        Path to the created chapter directory.
    """
    if base_dir is None:
        base_dir = Path.cwd() / "novel-to-comic-output"
    else:
        base_dir = Path(base_dir)

    novel_slug = _sanitize(novel_name)
    chapter_slug = _sanitize(chapter_title)

    novel_dir = base_dir / novel_slug
    chapter_dir = novel_dir / chapter_slug

    chapter_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Created directory: {chapter_dir}")
    return chapter_dir


def _sanitize(name):
    """Remove or replace characters unsafe for folder/file names."""
    name = re.sub(r'[<>:"/\\|?*]', "_", str(name))
    name = re.sub(r"\s+", " ", name).strip().rstrip(". ")
    if len(name) > 80:
        name = name[:80].rstrip(". ")
    name = name or "untitled"

    reserved_names = {"CON", "PRN", "AUX", "NUL"}
    reserved_names.update(f"COM{number}" for number in range(1, 10))
    reserved_names.update(f"LPT{number}" for number in range(1, 10))
    if name.split(".", 1)[0].upper() in reserved_names:
        name = f"_{name}"
    return name


def _extract_text_from_html(source: str) -> str | None:
    """Extract text from common chapter containers in an HTML document."""
    class ChapterParser(HTMLParser):
        VOID_ELEMENTS = {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.depth = 0
            self.fragments = []

        def handle_starttag(self, tag, attrs):
            if self.depth:
                if tag not in self.VOID_ELEMENTS:
                    self.depth += 1
                return

            attributes = dict(attrs)
            classes = set(attributes.get("class", "").split())
            is_content = (
                attributes.get("id") in {"content", "chaptercontent"}
                or bool(classes & {"content", "chapter-content"})
                or tag == "article"
            )
            if is_content:
                self.depth = 1

        def handle_startendtag(self, tag, attrs):
            return

        def handle_endtag(self, tag):
            if self.depth and tag not in self.VOID_ELEMENTS:
                self.depth -= 1

        def handle_data(self, data):
            if self.depth and data.strip():
                self.fragments.append(data.strip())

    parser = ChapterParser()
    parser.feed(source)
    parser.close()
    text = "".join(parser.fragments).strip()
    return text or None


def _attempt_error(strategy, error):
    diagnostic = f"{strategy}: {type(error).__name__}"
    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int) and 100 <= status_code <= 599:
        diagnostic += f" (HTTP {status_code})"
    return diagnostic


def extract_text_from_url_with_diagnostics(url: str) -> ExtractionResult:
    """Extract chapter text and report each strategy attempted."""
    parsed_url = urlparse(url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        return ExtractionResult(
            None, ("URL validation: expected http/https URL with a host",)
        )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    attempts = []

    try:
        import requests
        from readability import Document

        resp = requests.get(url, timeout=30, headers=headers)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        doc = Document(resp.text)
        text = _extract_text_from_html(doc.summary())
        if text:
            attempts.append("readability: success")
            return ExtractionResult(text, tuple(attempts))
        attempts.append("readability: no text extracted")
    except Exception as error:
        attempts.append(_attempt_error("readability", error))

    try:
        from newspaper import Article, Config

        config = Config()
        config.request_timeout = 30
        config.browser_user_agent = headers["User-Agent"]
        article = Article(url, config=config)
        article.download()
        if getattr(article, "download_state", None) == 2:
            attempts.append("newspaper: download failed")
        else:
            article.parse()
            text = article.text.strip()
            if text:
                attempts.append("newspaper: success")
                return ExtractionResult(text, tuple(attempts))
            attempts.append("newspaper: no text extracted")
    except Exception as error:
        attempts.append(_attempt_error("newspaper", error))

    try:
        import requests

        resp = requests.get(url, timeout=30, headers=headers)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        text = _extract_text_from_html(resp.text)
        if text:
            attempts.append("basic: success")
            return ExtractionResult(text, tuple(attempts))
        attempts.append("basic: no text extracted")
    except Exception as error:
        attempts.append(_attempt_error("basic", error))

    return ExtractionResult(None, tuple(attempts))


def extract_text_from_url(url: str) -> str | None:
    """Try to extract chapter text from a URL."""
    return extract_text_from_url_with_diagnostics(url).text


def load_characters(novel_dir):
    """Load character descriptions from JSON file."""
    char_file = Path(novel_dir) / "characters.json"
    if char_file.exists():
        try:
            with open(char_file, "r", encoding="utf-8") as f:
                characters = json.load(f)
        except json.JSONDecodeError as error:
            raise CharacterDataError(
                f"Invalid JSON in character data file {char_file}: {error.msg}"
            ) from error
        if not isinstance(characters, dict):
            raise CharacterDataError(
                f"Character data file {char_file} must contain a JSON object"
            )
        return characters
    return {}


def save_characters(novel_dir, characters):
    """Save character descriptions to JSON file."""
    char_file = Path(novel_dir) / "characters.json"
    if not isinstance(characters, dict):
        raise CharacterDataError("Character data must be a JSON object")
    if char_file.exists():
        load_characters(novel_dir)

    temp_path = None
    try:
        serialized = json.dumps(characters, ensure_ascii=False, indent=2)
        char_file.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=char_file.parent,
            prefix=f".{char_file.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(serialized)
        os.replace(temp_path, char_file)
    except Exception as error:
        raise CharacterDataError(
            f"Failed to save character data file {char_file}: {error}"
        ) from error
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
    print(f"[OK] Saved character info: {char_file}")


def generate_scene_filename(scene_num, description, ext=".png"):
    """Generate a descriptive filename for a scene image."""
    slug = _sanitize(description)
    if len(slug) > 40:
        slug = slug[:40].rstrip("_")
    if ext and not ext.startswith("."):
        ext = f".{ext}"
    return f"scene-{scene_num:02d}-{slug}{ext}"


def place_generated_image(
    source_path,
    novel_name,
    chapter_title,
    scene_num,
    description,
    base_dir=None,
):
    """Copy a generated image into the novel/chapter output structure."""
    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(f"Generated image does not exist: {source}")

    chapter_dir = create_output_dir(novel_name, chapter_title, base_dir)
    filename = generate_scene_filename(
        scene_num, description, source.suffix or ".png"
    )
    target = chapter_dir / filename
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target


def main() -> int:
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Novel to Comic helper")
    parser.add_argument("--url", help="URL of the novel chapter")
    parser.add_argument("--text-output",
                        help="Write the complete extracted chapter to this file")
    parser.add_argument("--novel", help="Novel name")
    parser.add_argument("--chapter", help="Chapter title")
    parser.add_argument("--output", help="Base output directory")
    parser.add_argument("--create-dir", action="store_true",
                        help="Create output directory structure")
    parser.add_argument("--place-image",
                        help="Copy a generated image into the chapter directory")
    parser.add_argument("--scene", type=int, help="Scene number for --place-image")
    parser.add_argument("--description",
                        help="Scene description for --place-image")

    args = parser.parse_args()

    if args.url:
        result = extract_text_from_url_with_diagnostics(args.url)
        if result.text:
            if args.text_output:
                text_output = Path(args.text_output)
                text_output.parent.mkdir(parents=True, exist_ok=True)
                text_output.write_text(result.text, encoding="utf-8")
                print(f"[OK] Saved complete chapter text: {text_output}")
            print(f"[OK] Extracted {len(result.text)} characters from URL")
            print("--- Preview (first 200 chars) ---")
            print(result.text[:200])
        else:
            print("[ERROR] Failed to extract text from URL", file=sys.stderr)
            for attempt in result.attempts:
                print(attempt, file=sys.stderr)
            return 1

    if args.create_dir and args.novel and args.chapter:
        chapter_dir = create_output_dir(args.novel, args.chapter, args.output)
        print(f"[OK] Output directory: {chapter_dir}")

    if args.place_image:
        missing = [
            name for name, value in (
                ("--novel", args.novel),
                ("--chapter", args.chapter),
                ("--scene", args.scene),
                ("--description", args.description),
            )
            if value is None
        ]
        if missing:
            parser.error(f"--place-image requires {', '.join(missing)}")
        target = place_generated_image(
            args.place_image,
            args.novel,
            args.chapter,
            args.scene,
            args.description,
            args.output,
        )
        print(f"[OK] Archived generated image: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
