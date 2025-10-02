"""Text file handling for simple line management."""

from pathlib import Path
from typing import Self

from .core import BaseHandle
from .utils import File


class TextHandle(BaseHandle):
    """Text file line management."""

    def __init__(self, path: str | Path | File):
        super().__init__(path)
        self.lines = []
        self._loaded = False

    def _parse(self, content: str):
        """Parse content into lines."""
        self.lines = content.splitlines(keepends=False) if content else []

    def _dump(self) -> str:
        """Dump lines to string."""
        return "\n".join(self.lines) + ("\n" if self.lines else "")

    def _ensure_loaded(self):
        """Ensure document is loaded."""
        if not self._loaded:
            self.load()

    def load(self) -> Self:
        """Load content from file (idempotent)."""
        if self.file.exists():
            content = self.file.read_text(encoding="utf-8")
            self._parse(content)
        else:
            self.lines = []
        self._loaded = True
        return self

    def present(self, line: str) -> Self:
        """Ensure line exists in file (idempotent)."""
        self._ensure_loaded()
        if line not in self.lines:
            self.lines.append(line)
        return self

    def absent(self, line: str) -> Self:
        """Ensure line doesn't exist in file (idempotent)."""
        self._ensure_loaded()
        while line in self.lines:
            self.lines.remove(line)
        return self

    def save(self, path: str | Path | None = None, *, stage: bool | None = None) -> None:
        """Save content to file.

        Args:
            path: Optional target path
            stage: Whether to stage to Plan (default: True if path is None, False if path is provided)

        Behavior:
        - save(): Stage to plan (stage defaults to True)
        - save(stage=False): Write directly to original file
        - save(path="new.txt"): Write directly to new file (stage defaults to False)
        - save(path="new.txt", stage=True): Stage write to new file operation
        """
        self._ensure_loaded()

        # Auto-infer stage default
        if stage is None:
            stage = path is None

        # Determine target path
        target_path = Path(path) if path else self.path

        if stage:
            # Stage to plan
            from .plan import plan

            plan.stage(target_path, self._get_serialized_content())
        else:
            # Write directly to file
            target_file = File(str(target_path))
            # Create parent directories for local files
            if hasattr(target_file.path, "parent") and hasattr(target_file.path.parent, "mkdir"):
                target_file.path.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(self._get_serialized_content(), encoding="utf-8")
