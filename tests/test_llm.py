"""Unit tests for the LLM helper and new config knobs (no network/API)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from affiliate import llm  # noqa: E402
from affiliate.config import _normalize_effort  # noqa: E402
from affiliate.content_generator import ARTICLE_SCHEMA  # noqa: E402
from affiliate.topic_research import TOPICS_SCHEMA  # noqa: E402


class EffortTests(unittest.TestCase):
    def test_valid_levels_pass_through(self):
        for level in ["low", "medium", "high", "xhigh", "max"]:
            self.assertEqual(_normalize_effort(level), level)

    def test_case_and_whitespace_normalized(self):
        self.assertEqual(_normalize_effort("  HIGH "), "high")

    def test_invalid_falls_back_to_high(self):
        self.assertEqual(_normalize_effort("turbo"), "high")
        self.assertEqual(_normalize_effort(""), "high")


class FenceStripTests(unittest.TestCase):
    def test_plain_json_untouched(self):
        self.assertEqual(llm._strip_fences('{"a": 1}'), '{"a": 1}')

    def test_json_fence_removed(self):
        self.assertEqual(llm._strip_fences('```json\n{"a": 1}\n```'), '{"a": 1}')

    def test_bare_fence_removed(self):
        self.assertEqual(llm._strip_fences('```\n{"a": 1}\n```'), '{"a": 1}')


class SchemaTests(unittest.TestCase):
    def _assert_objects_closed(self, schema: dict) -> None:
        """Structured outputs require additionalProperties:false on every object."""
        if schema.get("type") == "object":
            self.assertFalse(
                schema.get("additionalProperties", True),
                msg=f"object missing additionalProperties:false: {schema.get('properties', {}).keys()}",
            )
            for sub in schema.get("properties", {}).values():
                self._assert_objects_closed(sub)
        if schema.get("type") == "array":
            self._assert_objects_closed(schema.get("items", {}))

    def test_article_schema_closed(self):
        self._assert_objects_closed(ARTICLE_SCHEMA)

    def test_topics_schema_closed(self):
        self._assert_objects_closed(TOPICS_SCHEMA)

    def test_article_schema_has_core_fields(self):
        props = ARTICLE_SCHEMA["properties"]
        for field in ["title", "summary", "products", "faq", "closing"]:
            self.assertIn(field, props)


if __name__ == "__main__":
    unittest.main()
