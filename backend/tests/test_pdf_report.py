"""Tests for Premium PDF Report Generator."""

import pytest

from services.pdf_report import (
    PDFReportBuilder,
    ReportData,
    ReportError,
    generate_pdf_report,
)


@pytest.fixture
def sample_scores():
    return {
        "activity": 85.2,
        "collaboration": 72.1,
        "stack_diversity": 68.5,
        "ai_savviness": 45.3,
    }


@pytest.fixture
def sample_archetype():
    return {
        "name": "Full-Stack Polyglot",
        "description": "Versatile developer across multiple stacks",
    }


@pytest.fixture
def sample_ai_analysis():
    return {
        "overall_bucket": "moderate",
        "detected_tools": ["copilot", "cursor"],
        "confidence": "high",
        "burst_score": 35,
    }


@pytest.fixture
def sample_tech_profile():
    return {
        "languages": [
            {"name": "Python", "percentage": 45.2},
            {"name": "TypeScript", "percentage": 30.1},
            {"name": "Go", "percentage": 15.0},
        ],
        "frameworks": ["FastAPI", "React", "Next.js"],
    }


@pytest.fixture
def sample_branding():
    return {
        "company_name": "ACME Corp",
        "watermark_text": "ACME Analytics",
    }


@pytest.fixture
def report_data(sample_scores, sample_archetype, sample_ai_analysis, sample_tech_profile):
    return ReportData(
        scores=sample_scores,
        archetype=sample_archetype,
        ai_analysis=sample_ai_analysis,
        tech_profile=sample_tech_profile,
    )


# --- ReportData Tests ---


class TestReportData:
    def test_creation(self, report_data):
        assert report_data.scores["activity"] == 85.2
        assert report_data.archetype["name"] == "Full-Stack Polyglot"
        assert report_data.generated_at != ""

    def test_defaults(self):
        data = ReportData(scores={}, archetype={}, ai_analysis={}, tech_profile={})
        assert data.calendar == {}
        assert data.branding == {}

    def test_with_branding(self, sample_scores, sample_archetype):
        data = ReportData(
            scores=sample_scores,
            archetype=sample_archetype,
            ai_analysis={},
            tech_profile={},
            branding={"company_name": "Test Corp"},
        )
        assert data.branding["company_name"] == "Test Corp"


# --- PDFReportBuilder Tests ---


class TestPDFReportBuilder:
    def test_init_default(self):
        builder = PDFReportBuilder()
        assert builder._branding == {}

    def test_init_with_branding(self, sample_branding):
        builder = PDFReportBuilder(branding=sample_branding)
        assert builder._branding["company_name"] == "ACME Corp"

    def test_page_dimensions(self):
        assert PDFReportBuilder.PAGE_WIDTH == 595.28
        assert PDFReportBuilder.PAGE_HEIGHT == 841.89
        assert PDFReportBuilder.MARGIN == 50

    def test_generate_scorecard_returns_bytes(self, report_data):
        builder = PDFReportBuilder()
        result = builder.generate_scorecard(report_data)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_pdf_starts_with_header(self, report_data):
        builder = PDFReportBuilder()
        pdf = builder.generate_scorecard(report_data)
        assert pdf.startswith(b"%PDF-1.4")

    def test_pdf_ends_with_eof(self, report_data):
        builder = PDFReportBuilder()
        pdf = builder.generate_scorecard(report_data)
        assert pdf.rstrip().endswith(b"%%EOF")

    def test_pdf_contains_catalog(self, report_data):
        builder = PDFReportBuilder()
        pdf = builder.generate_scorecard(report_data)
        assert b"/Type /Catalog" in pdf

    def test_pdf_contains_page(self, report_data):
        builder = PDFReportBuilder()
        pdf = builder.generate_scorecard(report_data)
        assert b"/Type /Page" in pdf

    def test_pdf_contains_font(self, report_data):
        builder = PDFReportBuilder()
        pdf = builder.generate_scorecard(report_data)
        assert b"/BaseFont /Helvetica" in pdf

    def test_pdf_contains_scores(self, report_data):
        builder = PDFReportBuilder()
        pdf = builder.generate_scorecard(report_data)
        assert b"Activity" in pdf
        assert b"Collaboration" in pdf
        assert b"85.2" in pdf

    def test_pdf_contains_archetype(self, report_data):
        builder = PDFReportBuilder()
        pdf = builder.generate_scorecard(report_data)
        assert b"Full-Stack Polyglot" in pdf

    def test_pdf_contains_ai_analysis(self, report_data):
        builder = PDFReportBuilder()
        pdf = builder.generate_scorecard(report_data)
        assert b"moderate" in pdf
        assert b"copilot" in pdf

    def test_pdf_contains_languages(self, report_data):
        builder = PDFReportBuilder()
        pdf = builder.generate_scorecard(report_data)
        assert b"Python" in pdf
        assert b"TypeScript" in pdf

    def test_pdf_with_branding(self, report_data, sample_branding):
        report_data.branding = sample_branding
        builder = PDFReportBuilder(branding=sample_branding)
        pdf = builder.generate_scorecard(report_data)
        assert b"ACME Corp" in pdf

    def test_score_bar(self):
        bar = PDFReportBuilder._score_bar(50, width=10)
        assert bar == "[#####.....]"

    def test_score_bar_full(self):
        bar = PDFReportBuilder._score_bar(100, width=10)
        assert bar == "[##########]"

    def test_score_bar_empty(self):
        bar = PDFReportBuilder._score_bar(0, width=10)
        assert bar == "[..........]"

    def test_score_bar_default_width(self):
        bar = PDFReportBuilder._score_bar(75)
        assert len(bar) == 22  # "[" + 20 chars + "]"

    def test_build_content_has_sections(self, report_data):
        builder = PDFReportBuilder()
        lines = builder._build_content(report_data, "Test Corp")
        content = "\n".join(lines)
        assert "Test Corp Developer Scorecard" in content
        assert "DIMENSION SCORES" in content
        assert "DEVELOPER ARCHETYPE" in content
        assert "AI ANALYSIS" in content
        assert "TECHNOLOGY PROFILE" in content

    def test_build_content_overall_score(self, report_data):
        builder = PDFReportBuilder()
        lines = builder._build_content(report_data, "GPS")
        content = "\n".join(lines)
        # Overall should be average: (85.2+72.1+68.5+45.3)/4 ≈ 67.8
        assert "Overall Score" in content

    def test_build_content_empty_scores(self):
        data = ReportData(scores={}, archetype={}, ai_analysis={}, tech_profile={})
        builder = PDFReportBuilder()
        lines = builder._build_content(data, "GPS")
        content = "\n".join(lines)
        assert "Overall Score: 0" in content

    def test_pdf_stream_has_text_operators(self, report_data):
        builder = PDFReportBuilder()
        lines = builder._build_content(report_data, "GPS")
        stream = builder._build_pdf_stream(lines)
        assert "BT" in stream
        assert "ET" in stream
        assert "/F1" in stream
        assert "Tf" in stream
        assert "Td" in stream
        assert "Tj" in stream


# --- Convenience function ---


class TestGeneratePdfReport:
    def test_returns_valid_pdf(
        self,
        sample_scores,
        sample_archetype,
        sample_ai_analysis,
        sample_tech_profile,
    ):
        pdf = generate_pdf_report(
            scores=sample_scores,
            archetype=sample_archetype,
            ai_analysis=sample_ai_analysis,
            tech_profile=sample_tech_profile,
        )
        assert isinstance(pdf, bytes)
        assert pdf.startswith(b"%PDF-1.4")

    def test_with_branding(
        self,
        sample_scores,
        sample_archetype,
        sample_ai_analysis,
        sample_tech_profile,
        sample_branding,
    ):
        pdf = generate_pdf_report(
            scores=sample_scores,
            archetype=sample_archetype,
            ai_analysis=sample_ai_analysis,
            tech_profile=sample_tech_profile,
            branding=sample_branding,
        )
        assert b"ACME Corp" in pdf

    def test_empty_data(self):
        pdf = generate_pdf_report(scores={}, archetype={}, ai_analysis={}, tech_profile={})
        assert isinstance(pdf, bytes)
        assert len(pdf) > 100


# --- Error class ---


class TestReportError:
    def test_defaults(self):
        err = ReportError()
        assert err.code == "REPORT_ERROR"
        assert err.status_code == 500

    def test_custom_message(self):
        err = ReportError("PDF generation timed out")
        assert err.message == "PDF generation timed out"
