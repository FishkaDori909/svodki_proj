"""Превращение готовой сводки в PDF через LibreOffice (если он установлен)."""
import glob
import shutil
import subprocess
import tempfile
from pathlib import Path


class PdfConversionError(Exception):
    pass


_EXTRA_SOFFICE_GLOBS = (
    "/opt/libreoffice*/program/soffice",
    "/usr/lib/libreoffice*/program/soffice",
    "C:/Program Files/LibreOffice/program/soffice.exe",
)


def find_soffice():
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    for pattern in _EXTRA_SOFFICE_GLOBS:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]
    return None


def to_pdf(xlsx_path, out_dir=None, timeout: int = 120) -> Path:
    xlsx_path = Path(xlsx_path)
    out_dir = Path(out_dir) if out_dir else xlsx_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    soffice = find_soffice()
    if not soffice:
        raise PdfConversionError("LibreOffice не установлен")

    with tempfile.TemporaryDirectory(prefix="lo_svodka_profile_") as profile_dir:
        cmd = [
            soffice, "--headless", "--norestore", "--invisible",
            f"-env:UserInstallation={Path(profile_dir).as_uri()}",
            "--convert-to", "pdf", "--outdir", str(out_dir), str(xlsx_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise PdfConversionError(f"LibreOffice не ответил за {timeout} с")
        except OSError as e:
            raise PdfConversionError(f"Не удалось запустить LibreOffice: {e}")

    pdf_path = out_dir / (xlsx_path.stem + ".pdf")
    if result.returncode != 0 or not pdf_path.exists():
        raise PdfConversionError(
            f"LibreOffice завершился с кодом {result.returncode}: "
            f"{(result.stderr or result.stdout).strip()[:300]}")
    return pdf_path
