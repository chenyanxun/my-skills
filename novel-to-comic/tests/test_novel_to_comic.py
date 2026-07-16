import importlib.util
import io
from contextlib import ExitStack
from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "novel_to_comic.py"
SPEC = importlib.util.spec_from_file_location("novel_to_comic", MODULE_PATH)
novel_to_comic = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = novel_to_comic
SPEC.loader.exec_module(novel_to_comic)


class NovelToComicTests(unittest.TestCase):
    def test_extract_text_from_html_joins_content_paragraphs(self):
        source = (
            '<div id="content"><p>第一段。</p><p>第二段。</p></div>'
        )

        self.assertEqual(
            novel_to_comic._extract_text_from_html(source),
            "第一段。第二段。",
        )

    def test_extraction_result_is_frozen(self):
        result = novel_to_comic.ExtractionResult(None, ("readability: failed",))

        with self.assertRaises(FrozenInstanceError):
            result.text = "changed"

    def test_extract_text_from_html_ignores_void_elements_and_footer(self):
        source = (
            '<div id="content"><div>正文<br><img src="cover.jpg">继续</div></div>'
            "<footer>页脚</footer>"
        )

        self.assertEqual(novel_to_comic._extract_text_from_html(source), "正文继续")

    def test_attempt_error_redacts_sensitive_exception_details(self):
        url = "https://user:pass@example.com/x?token=secret"
        error = RuntimeError(f"download failed for {url}")
        error.response = type("Response", (), {"status_code": 401})()

        diagnostic = novel_to_comic._attempt_error("readability", error)

        self.assertIn("RuntimeError", diagnostic)
        self.assertIn("HTTP 401", diagnostic)
        for secret in (url, "user", "pass", "token", "secret"):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, diagnostic)

    def test_diagnostic_extraction_rejects_invalid_urls(self):
        for url in ("ftp://example.com/chapter", "https:///chapter"):
            with self.subTest(url=url):
                result = novel_to_comic.extract_text_from_url_with_diagnostics(url)

                self.assertIsNone(result.text)
                self.assertTrue(result.attempts)
                self.assertIn("URL", result.attempts[0])

    def test_diagnostic_extraction_records_each_failed_strategy_in_order(self):
        original_import = __import__

        def fail_optional_imports(name, *args, **kwargs):
            if name in {"readability", "newspaper", "requests"}:
                raise ImportError(f"{name} unavailable")
            return original_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=fail_optional_imports):
            result = novel_to_comic.extract_text_from_url_with_diagnostics(
                "https://example.com/chapter"
            )

        self.assertIsNone(result.text)
        self.assertEqual(len(result.attempts), 3)
        self.assertTrue(result.attempts[0].startswith("readability:"))
        self.assertTrue(result.attempts[1].startswith("newspaper:"))
        self.assertTrue(result.attempts[2].startswith("basic:"))
        self.assertTrue(all("ImportError" in item for item in result.attempts))

    def test_newspaper_receives_timeout_and_user_agent_and_reports_download_error(
        self,
    ):
        captured = {}
        requests_module = ModuleType("requests")
        readability_module = ModuleType("readability")
        newspaper_module = ModuleType("newspaper")

        def failed_get(*args, **kwargs):
            raise RuntimeError("requests download failed")

        class Document:
            pass

        class Config:
            pass

        class Article:
            def __init__(self, url, config=None):
                captured["url"] = url
                captured["config"] = config
                self.text = ""

            def download(self):
                raise RuntimeError("newspaper download failed")

            def parse(self):
                raise AssertionError("parse must not run after download failure")

        requests_module.get = failed_get
        readability_module.Document = Document
        newspaper_module.Config = Config
        newspaper_module.Article = Article

        with mock.patch.dict(
            sys.modules,
            {
                "requests": requests_module,
                "readability": readability_module,
                "newspaper": newspaper_module,
            },
        ):
            result = novel_to_comic.extract_text_from_url_with_diagnostics(
                "https://example.com/chapter"
            )

        config = captured["config"]
        self.assertEqual(config.request_timeout, 30)
        self.assertIn("Mozilla/5.0", config.browser_user_agent)
        self.assertEqual(captured["url"], "https://example.com/chapter")
        self.assertIn("newspaper: RuntimeError", result.attempts[1])

    def test_extract_text_from_url_preserves_optional_string_api(self):
        expected = novel_to_comic.ExtractionResult("正文", ("basic: success",))
        with mock.patch.object(
            novel_to_comic,
            "extract_text_from_url_with_diagnostics",
            return_value=expected,
        ):
            self.assertEqual(
                novel_to_comic.extract_text_from_url(
                    "https://example.com/chapter"
                ),
                "正文",
            )

    def test_main_writes_attempts_to_stderr_and_returns_one_on_failure(self):
        result = novel_to_comic.ExtractionResult(
            None,
            ("readability: unavailable", "newspaper: parse failed"),
        )
        stderr = io.StringIO()
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                novel_to_comic,
                "extract_text_from_url_with_diagnostics",
                return_value=result,
            ))
            stack.enter_context(mock.patch.object(
                sys, "argv", ["novel_to_comic.py", "--url", "https://example.com"]
            ))
            stack.enter_context(mock.patch("sys.stderr", stderr))
            return_code = novel_to_comic.main()

        self.assertEqual(return_code, 1)
        self.assertIn("readability: unavailable", stderr.getvalue())
        self.assertIn("newspaper: parse failed", stderr.getvalue())

    def test_main_returns_zero_on_success(self):
        result = novel_to_comic.ExtractionResult("正文", ("basic: success",))
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                novel_to_comic,
                "extract_text_from_url_with_diagnostics",
                return_value=result,
            ))
            stack.enter_context(mock.patch.object(
                sys, "argv", ["novel_to_comic.py", "--url", "https://example.com"]
            ))
            stack.enter_context(mock.patch("sys.stdout", io.StringIO()))
            self.assertEqual(novel_to_comic.main(), 0)

    def test_script_entry_point_raises_system_exit_from_main(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('raise SystemExit(main())', source)

    def test_sanitize_prefixes_windows_reserved_device_names(self):
        reserved_names = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            *(f"COM{number}" for number in range(1, 10)),
            *(f"LPT{number}" for number in range(1, 10)),
        ]

        for name in reserved_names:
            with self.subTest(name=name):
                sanitized = novel_to_comic._sanitize(name)
                self.assertNotEqual(sanitized.upper(), name)
                self.assertTrue(sanitized)

    def test_sanitize_strips_trailing_dots_and_spaces(self):
        self.assertEqual(novel_to_comic._sanitize("chapter.  "), "chapter")

    def test_generate_scene_filename_accepts_extensions_with_or_without_dot(self):
        self.assertEqual(
            novel_to_comic.generate_scene_filename(1, "opening", "jpg"),
            "scene-01-opening.jpg",
        )
        self.assertEqual(
            novel_to_comic.generate_scene_filename(1, "opening", ".jpg"),
            "scene-01-opening.jpg",
        )

    def test_load_characters_reports_malformed_json_with_file_path(self):
        with tempfile.TemporaryDirectory() as directory:
            char_file = Path(directory) / "characters.json"
            char_file.write_text("{broken", encoding="utf-8")

            with self.assertRaises(novel_to_comic.CharacterDataError) as error:
                novel_to_comic.load_characters(directory)

            self.assertIn(str(char_file), str(error.exception))
            self.assertIn("JSON", str(error.exception))

    def test_load_characters_rejects_non_object_json(self):
        with tempfile.TemporaryDirectory() as directory:
            char_file = Path(directory) / "characters.json"
            char_file.write_text('["not", "an", "object"]', encoding="utf-8")

            with self.assertRaises(novel_to_comic.CharacterDataError) as error:
                novel_to_comic.load_characters(directory)

            self.assertIn(str(char_file), str(error.exception))

    def test_save_characters_does_not_overwrite_malformed_existing_json(self):
        with tempfile.TemporaryDirectory() as directory:
            char_file = Path(directory) / "characters.json"
            original = "{broken"
            char_file.write_text(original, encoding="utf-8")

            with self.assertRaises(novel_to_comic.CharacterDataError):
                novel_to_comic.save_characters(
                    directory, {"阿青": {"hair": "black"}}
                )

            self.assertEqual(char_file.read_text(encoding="utf-8"), original)

    def test_save_characters_preserves_existing_file_on_serialization_error(self):
        with tempfile.TemporaryDirectory() as directory:
            char_file = Path(directory) / "characters.json"
            original = '{"阿青": {"hair": "black"}}'
            char_file.write_text(original, encoding="utf-8")

            with self.assertRaises(novel_to_comic.CharacterDataError) as error:
                novel_to_comic.save_characters(
                    directory, {"阿青": {"aliases": {"青儿"}}}
                )

            self.assertIn(str(char_file), str(error.exception))
            self.assertEqual(char_file.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
