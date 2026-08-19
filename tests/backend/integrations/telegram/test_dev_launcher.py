from pathlib import Path


def test_windows_dev_launcher_loads_dotenv_for_telegram_polling() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    launcher = (repo_root / "scripts" / "start_dev.ps1").read_text(encoding="utf-8")

    assert "uvicorn app.main:app --env-file .env" in launcher
