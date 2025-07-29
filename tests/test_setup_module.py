import pathlib
import pytest

import test_setup


def test_check_python_version():
    assert test_setup.check_python_version() is True


def test_check_required_files(tmp_path):
    base = tmp_path
    (base / 'app.py').write_text('')
    (base / 'requirements.txt').write_text('')
    assert test_setup.check_required_files(base)


def test_check_packages():
    assert test_setup.check_packages(["sys"])


def test_check_templates_dir(tmp_path):
    path = tmp_path / 'templates'
    path.mkdir()
    (path / 'example.html').write_text('<html></html>')
    files = test_setup.check_templates_dir(tmp_path)
    assert 'example.html' in files


def test_run_checks(tmp_path, monkeypatch):
    (tmp_path / 'app.py').write_text('')
    (tmp_path / 'requirements.txt').write_text('')
    (tmp_path / 'templates').mkdir()
    monkeypatch.chdir(tmp_path)
    assert test_setup.run_checks(interactive=False) is None
