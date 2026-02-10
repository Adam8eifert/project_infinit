import os
from pathlib import Path
import pytest

from processing import manual_csv


class DummyLoader:
    def __init__(self, calls):
        self.calls = calls

    def load_csv_to_sources(self, path):
        self.calls.append(path)


def test_process_manual_csvs_moves_and_imports(tmp_path, monkeypatch):
    manual = tmp_path / "manual"
    target = tmp_path / "export" / "csv"
    manual.mkdir(parents=True)
    target.mkdir(parents=True)

    # Create sample CSV
    # Create a sample CSV that is already valid
    sample = manual / "sample.csv"
    sample.write_text("source_name,source_type,title,url,text,scraped_at\n")

    calls = []
    dummy = DummyLoader(calls)
    # Patch CSVtoDatabaseLoader in module to use dummy
    monkeypatch.setattr("processing.manual_csv.CSVtoDatabaseLoader", lambda: dummy)

    processed = manual_csv.process_manual_csvs(manual_dir=str(manual), target_dir=str(target), do_import=True)

    assert len(processed) == 1
    dest = processed[0]
    assert dest.exists()
    assert len(calls) == 1
    assert str(dest) == str(calls[0])


def test_process_manual_csvs_normalizes_columns(tmp_path, monkeypatch):
    manual = tmp_path / "manual_norm"
    target = tmp_path / "export" / "csv"
    manual.mkdir(parents=True)
    target.mkdir(parents=True)

    # Create sample CSV missing required columns but with aliases
    sample = manual / "misscols.csv"
    sample.write_text("content,link,date_published\nhello world,https://ex/1,2020-01-01T00:00:00Z\n")

    calls = []
    dummy = DummyLoader(calls)
    monkeypatch.setattr("processing.manual_csv.CSVtoDatabaseLoader", lambda: dummy)

    processed = manual_csv.process_manual_csvs(manual_dir=str(manual), target_dir=str(target), do_import=True)
    assert len(processed) == 1
    dest = processed[0]
    # After normalization the file must have required columns
    import pandas as pd
    df = pd.read_csv(dest)
    for col in ["source_name", "source_type", "title", "url", "text", "scraped_at"]:
        assert col in df.columns
    assert len(calls) == 1
    assert str(dest) == str(calls[0])


def test_process_manual_csvs_creates_dir_if_missing(tmp_path):
    manual = tmp_path / "manual2"
    target = tmp_path / "export" / "csv"

    # Ensure dirs do not exist
    assert not manual.exists()
    processed = manual_csv.process_manual_csvs(manual_dir=str(manual), target_dir=str(target), do_import=False)
    # No files to process, returns empty list but directory created
    assert processed == []
    assert manual.exists()
