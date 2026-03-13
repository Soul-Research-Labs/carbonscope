"""Tests for api/services/templates.py — questionnaire templates catalog."""

from __future__ import annotations

import pytest

from api.services.templates import TEMPLATES, get_template, list_templates

EXPECTED_IDS = ["cdp_climate", "ecovadis_environment", "tcfd_disclosure", "ghg_protocol_inventory", "csrd_esrs_climate"]


class TestListTemplates:
    def test_returns_all_templates(self):
        result = list_templates()
        assert len(result) == len(EXPECTED_IDS)

    def test_summary_has_required_keys(self):
        result = list_templates()
        for item in result:
            assert "id" in item
            assert "title" in item
            assert "description" in item
            assert "framework" in item
            assert "question_count" in item

    def test_question_count_matches(self):
        result = list_templates()
        for item in result:
            template = TEMPLATES[item["id"]]
            assert item["question_count"] == len(template["questions"])

    def test_ids_match_expected(self):
        result = list_templates()
        ids = [t["id"] for t in result]
        assert set(ids) == set(EXPECTED_IDS)

    def test_no_questions_in_summary(self):
        """list_templates should NOT include the full questions list."""
        result = list_templates()
        for item in result:
            assert "questions" not in item


class TestGetTemplate:
    def test_known_template_returns_dict(self):
        result = get_template("cdp_climate")
        assert result is not None
        assert result["id"] == "cdp_climate"
        assert "questions" in result

    def test_unknown_template_returns_none(self):
        assert get_template("nonexistent_template") is None

    @pytest.mark.parametrize("template_id", EXPECTED_IDS)
    def test_each_template_retrievable(self, template_id: str):
        result = get_template(template_id)
        assert result is not None
        assert result["id"] == template_id
        assert isinstance(result["questions"], list)
        assert len(result["questions"]) > 0

    def test_template_questions_have_required_fields(self):
        for tid in EXPECTED_IDS:
            result = get_template(tid)
            for q in result["questions"]:
                assert "question_text" in q
                assert "category" in q
