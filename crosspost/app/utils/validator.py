from pathlib import Path

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS
MAX_FILE_SIZE = 500 * 1024 * 1024


def validate_file(filename: str, file_size: int, allowed_extensions: set[str] | None = None) -> tuple[bool, str]:
    allowed = allowed_extensions or ALLOWED_EXTENSIONS
    ext = Path(filename or "").suffix.lower()
    if not ext or ext not in allowed:
        return False, f"Format file {ext or 'tanpa ekstensi'} tidak didukung. Gunakan: {', '.join(sorted(allowed))}"
    if file_size > MAX_FILE_SIZE:
        return False, f"File terlalu besar. Maksimal {MAX_FILE_SIZE // (1024*1024)}MB"
    return True, ""


def validate_required_fields(data: dict, fields: list) -> list[str]:
    errors = []
    for field in fields:
        if field not in data or not data[field]:
            errors.append(f"Field '{field}' harus diisi")
    return errors
