from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from gridshift import exports


def test_report_page_count_uses_written_pages_not_next_page(tmp_path, monkeypatch):
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Flowable, PageBreak, Paragraph

    class EndMarker(Flowable):
        _gridshift_main_body_end = True

        def wrap(self, width, height):
            return 0, 0

        def draw(self):
            pass

    styles = getSampleStyleSheet()
    story = []
    for index in range(15):
        story.append(Paragraph(f"Verified report page {index + 1}", styles["Normal"]))
        if index < 14:
            story.append(PageBreak())
    story.append(EndMarker())
    monkeypatch.setattr(exports, "_pdf_story", lambda evidence: story)
    path = tmp_path / "report.pdf"
    assert exports._build_pdf(path, SimpleNamespace(study_id="page-count-fixture")) == (15, 15)
    assert path.read_bytes().startswith(b"%PDF-")


def test_export_refuses_missing_results_before_creating_outputs(tmp_path):
    with pytest.raises(FileNotFoundError, match="verified results are absent"):
        exports.export(tmp_path, {})

    assert not (tmp_path / "reports").exists()
    assert not (tmp_path / "slides").exists()
    assert not (tmp_path / "notebooks").exists()


def test_record_normalizer_accepts_arrays_and_nested_record_tables():
    assert exports._records(
        [{"model_id": "naive", "mae": 1.25}],
        "metrics",
    ) == [{"model_id": "naive", "mae": 1.25}]
    assert exports._records(
        {"records": [{"model_id": "daily", "mae": None}]},
        "metrics",
    ) == [{"model_id": "daily", "mae": None}]
    assert exports._format(float("nan")) == "NA"


def test_result_tables_allow_serialization_rounding_but_reject_changed_evidence():
    assert exports._tables_match(
        [{"model_id": "AR", "mae": 12.1234567891, "converged": True}],
        [{"model_id": "AR", "mae": "12.123456789123", "converged": "True"}],
    )
    assert not exports._tables_match([{"mae": 12.}], [{"mae": "12.001"}])
    assert not exports._tables_match([{"mae": 12.}], [{"rmse": "12."}])


def test_generated_notebook_is_offline_and_does_not_claim_execution(tmp_path):
    evidence = exports.Evidence(
        root=tmp_path,
        study_id="study-test",
        config={"study": {"reported_horizons": [1, 4]}},
        results={
            "forecast_champion": "ar",
            "strongest_simple": "daily_naive",
            "deployment_model": "daily_naive",
            "limitations": [],
        },
        quality={},
        diagnostics={},
        manifest={},
        protocol={},
        source_tables={},
        table_paths={},
        figures={},
        diagnostic_tables={},
        missing_diagnostic_tables=(),
        missing_diagnostic_figures=(),
        source_stages={},
    )

    notebook = exports._markdown_notebook(evidence)
    code = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    notebook_text = "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
    )

    assert notebook["nbformat"] == 4
    assert len(notebook["cells"]) >= 10
    assert all(
        cell["execution_count"] is None and cell["outputs"] == []
        for cell in notebook["cells"]
        if cell["cell_type"] == "code"
    )
    assert "requests.get" not in code
    assert "fit_model(" not in code
    assert "gridshift.study import run_dir" in code
    assert "VALIDATION_RUN.parent.name == STUDY_ID == TEST_RUN.parent.name" in code
    assert "model_*_parameters.json" in code
    assert "ljung_box.csv" in code
    assert "model_*_acf_pacf.csv" in code
    assert "model_*_diagnostics.png" in code
    assert "ARIMA(p,d,q)" in notebook_text
    assert "SARIMA" in notebook_text
    assert "augmentation lag is not an AR model order" in notebook_text
    assert "exp(mu + variance/2) - 1" in notebook_text
    assert "forecast_loss_bootstrap.csv" in code
    assert "versus_simple_bootstrap.csv" in code
    assert "Rejected work is not carbon saved" in notebook_text


def test_slide_content_has_twelve_notes_and_only_evidence_backed_chart_values(tmp_path):
    rows = [
        {
            "model_id": "ar",
            "group": "all",
            "horizon": 1,
            "n": 10,
            "mae": 2.5,
            "rmse": 3.0,
        },
        {
            "model_id": "daily_naive",
            "group": "all",
            "horizon": 1,
            "n": 10,
            "mae": 3.5,
            "rmse": 4.0,
        },
    ]
    evidence = exports.Evidence(
        root=tmp_path,
        study_id="study-test",
        config={"study": {}, "scheduling": {}},
        results={
            "forecast_champion": "ar",
            "strongest_simple": "daily_naive",
            "deployment_model": "daily_naive",
            "limitations": ["Scenario energy is not measured telemetry."],
        },
        quality={"observed": 10, "slots": 10},
        diagnostics={},
        manifest={},
        protocol={},
        source_tables={
            "validation_metrics": rows,
            "test_metrics": rows,
            "validation_common_metrics": rows,
            "test_common_metrics": rows,
            "primary_summary": [],
            "primary_bootstrap": [],
            "primary_monthly": [],
            "queue_summary": [],
        },
        table_paths={},
        figures={
            "series.png": tmp_path / "series.png",
            "stl48.png": tmp_path / "stl48.png",
            "missingness.png": tmp_path / "missingness.png",
        },
        diagnostic_tables={},
        missing_diagnostic_tables=(),
        missing_diagnostic_figures=(),
        source_stages={},
    )

    content = exports._presentation_content(evidence)

    assert len(content["slides"]) == 12
    assert all(slide["notes"].strip() for slide in content["slides"])
    assert content["slides"][-1]["title"] == "Backup equations and failures"
    assert "Job CO2 =" in content["slides"][-1]["bullets"][0]
    validation_chart = content["slides"][6]["chart"]
    assert validation_chart["categories"] == ["1"]
    assert validation_chart["series"][0]["values"] == [2.5]
    assert validation_chart["series"][1]["values"] == [3.5]
