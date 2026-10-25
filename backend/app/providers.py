from pathlib import Path
import shutil, uuid

class LocalStorageProvider:
    """Local-only adapter for development; not suitable for multi-instance production."""
    def __init__(self, upload_dir: Path):
        self.upload_dir = upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, source_path: Path, original_filename: str):
        suffix = Path(original_filename).suffix.lower()
        stored_name = uuid.uuid4().hex + suffix
        target = self.upload_dir / stored_name
        shutil.move(str(source_path), target)
        return stored_name, target

# Provider intentionally unselected: no Mux/Cloudflare credentials or paid integration.
