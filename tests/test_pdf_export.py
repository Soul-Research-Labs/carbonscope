"""Direct tests for api/services/pdf_export.py — PDF generation functions."""

from __future__ import annotations

import pytest

from api.services.pdf_export import generate_questionnaire_pdf, generate_report_pdf


class TestReportPDF:
    """Tests for generate_report_pdf."""

    def test_returns_bytes(self):
        result = generate_report_pdf(
            company_name="TestCorp",
            industry="manufacturing",
            region="US",
            year=2025,
            scope1=100.0,
            scope2=200.0,
            scope3=300.0,
            total=600.0,
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_pdf_header(self):
        result = generate_report_pdf(
            company_name="TestCorp",
            industry="technology",
            region="EU",
            year=2024,
            scope1=50.0,
            scope2=100.0,
            scope3=150.0,
            total=300.0,
        )
        # PDF files start with %PDF
        assert result[:5] == b"%PDF-"

    def test_with_optional_fields(self):
        result = generate_report_pdf(
            company_name="TestCorp",
            industry="finance",
            region="US",
            year=2025,
            scope1=100.0,
            scope2=200.0,
            scope3=300.0,
            total=600.0,
            methodology="ghg_protocol_v2025",
            confidence=0.85,
        )
        assert result[:5] == b"%PDF-"

    def test_zero_total_no_division_error(self):
        """When total is 0, percentage columns should show '—' not crash."""
        result = generate_report_pdf(
            company_name="TestCorp",
            industry="manufacturing",
            region="US",
            year=2025,
            scope1=0.0,
            scope2=0.0,
            scope3=0.0,
            total=0.0,
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_large_numbers(self):
        result = generate_report_pdf(
            company_name="MegaCorp International",
            industry="energy",
            region="GLOBAL",
            year=2025,
            scope1=1_000_000.5,
            scope2=2_000_000.25,
            scope3=5_000_000.75,
            total=8_000_001.5,
        )
        assert result[:5] == b"%PDF-"


class TestQuestionnairePDF:
    """Tests for generate_questionnaire_pdf."""

    def test_returns_bytes(self):
        result = generate_questionnaire_pdf(
            company_name="TestCorp",
            questionnaire_title="CDP Climate Change",
            questions=[
                {
                    "question_number": 1,
                    "question_text": "What are your Scope 1 emissions?",
                    "category": "emissions",
                    "human_answer": "100 tCO2e",
                    "status": "approved",
                },
            ],
        )
        assert isinstance(result, bytes)
        assert result[:5] == b"%PDF-"

    def test_empty_questions(self):
        result = generate_questionnaire_pdf(
            company_name="TestCorp",
            questionnaire_title="Empty Questionnaire",
            questions=[],
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_draft_answer_fallback(self):
        """When no human_answer, should use ai_draft_answer."""
        result = generate_questionnaire_pdf(
            company_name="TestCorp",
            questionnaire_title="AI Draft Test",
            questions=[
                {
                    "question_number": 1,
                    "question_text": "Describe your climate policy.",
                    "category": "governance",
                    "ai_draft_answer": "Our company has a comprehensive climate policy...",
                    "human_answer": None,
                    "status": "draft",
                },
            ],
        )
        assert result[:5] == b"%PDF-"

    def test_multiple_questions(self):
        questions = [
            {
                "question_number": i,
                "question_text": f"Question {i}?",
                "category": "emissions",
                "human_answer": f"Answer {i}",
                "status": "reviewed",
            }
            for i in range(1, 11)
        ]
        result = generate_questionnaire_pdf(
            company_name="TestCorp",
            questionnaire_title="10 Questions",
            questions=questions,
        )
        assert result[:5] == b"%PDF-"

    def test_missing_optional_fields(self):
        """Questions with missing optional fields should not crash."""
        result = generate_questionnaire_pdf(
            company_name="TestCorp",
            questionnaire_title="Minimal",
            questions=[
                {
                    "question_number": 1,
                    "question_text": "What?",
                },
            ],
        )
        assert isinstance(result, bytes)
