"""Asset Manager for saving, deduplicating, and serving extracted document figures and images."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Tuple


class AssetManager:
    """Manages disk-based persistence and URLs for extracted document figures and slide images."""

    def __init__(self, assets_dir: str = "./knowledge_assets"):
        self.assets_dir = Path(assets_dir).resolve()
        self.assets_dir.mkdir(parents=True, exist_ok=True)

    def save_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        preferred_ext: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Save image bytes to asset storage with content-hash deduplication.

        Returns:
            Tuple of (asset_id, asset_url) e.g. ("ast_a1b2c3d4", "/api/assets/ast_a1b2c3d4.png")
        """
        # Determine file extension
        ext = preferred_ext
        if not ext:
            mime_lower = (mime_type or "").lower()
            if "png" in mime_lower:
                ext = ".png"
            elif "jpeg" in mime_lower or "jpg" in mime_lower:
                ext = ".jpg"
            elif "gif" in mime_lower:
                ext = ".gif"
            elif "webp" in mime_lower:
                ext = ".webp"
            elif "svg" in mime_lower:
                ext = ".svg"
            else:
                ext = mimetypes.guess_extension(mime_type) or ".png"

        if not ext.startswith("."):
            ext = f".{ext}"

        # Hash image bytes for deterministic deduplication
        sha = hashlib.sha256(image_bytes).hexdigest()[:16]
        asset_id = f"ast_{sha}"
        filename = f"{asset_id}{ext}"
        target_path = self.assets_dir / filename

        # Write file if not already present
        if not target_path.exists():
            target_path.write_bytes(image_bytes)

        url = f"/api/assets/{filename}"
        return asset_id, url

    def get_asset_path(self, filename_or_id: str) -> Optional[Path]:
        """Resolve an asset ID or filename to its filesystem path."""
        # 1. Exact match in assets directory
        direct_path = self.assets_dir / filename_or_id
        if direct_path.exists() and direct_path.is_file():
            return direct_path

        # 2. Match without extension (e.g. ast_123456)
        matches = list(self.assets_dir.glob(f"{filename_or_id}.*"))
        if matches:
            return matches[0]

        return None

