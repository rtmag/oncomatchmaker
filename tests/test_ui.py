from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from test_matching import FakeClient

from trials.pipeline import match_patient

APP = Path(__file__).parents[1] / "app" / "main.py"


def test_demo_review_and_results(profile, record):
    result = match_patient(profile, client=FakeClient([record]))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert app.button[0].disabled
    app.checkbox[0].check().run()
    with patch("trials.pipeline.match_patient", return_value=result):
        app.button[0].click().run()
    assert not app.exception
    assert any("Experimental clinical trials" in h.value for h in app.subheader)
    app.selectbox[0].select("negative").run()
    assert not app.exception
    assert not any("Experimental clinical trials" in h.value for h in app.subheader)


def test_pdf_upload_available_and_invalid_json():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.radio[0].set_value("PDF report").run()
    assert not app.exception
    assert len(app.get("file_uploader")) == 1
    app.radio[0].set_value("Synthetic demo profile").run()
    app.text_area[0].set_value("{invalid")
    app.checkbox[0].check().run()
    app.button[0].click().run()
    assert not app.exception
    assert app.error
