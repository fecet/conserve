"""Core API for Conserve - BaseHandle only."""

from pathlib import Path

from .file import File


class BaseHandle:
    """Base class for all Handles with simplified Plan integration."""

    def __init__(self, path: str | Path | File):
        # Accept File instance or path
        self.file = path if isinstance(path, File) else File(path)
        self.path = self.file.path
        self._loaded = False

    def _parse(self, content: str):
        """Parse content into document. Format-specific implementation."""
        raise NotImplementedError

    def _dump(self) -> str:
        """Dump document to string. Format-specific implementation."""
        raise NotImplementedError

    def _get_serialized_content(self) -> str:
        """Return serialized content."""
        return self._dump()

    # --- Unified lifecycle helpers ---
    def _ensure_loaded(self) -> None:
        """Ensure underlying state is loaded exactly once."""
        if not self._loaded:
            self.load()

    def load(self):
        """Load from file if exists, otherwise parse empty content.

        Subclasses MUST implement `_parse`. This base method centralizes the
        idempotent load behavior shared by all handles.
        """
        if self.file.exists():
            content = self.file.read_text(encoding="utf-8")
            self._parse(content)
        else:
            # Parse empty content to initialize default state
            self._parse("")
        self._loaded = True
        return self

    def save(self, path: str | Path | None = None, *, stage: bool | None = None) -> None:
        """Persist current state to a file or stage via Plan.

        Behavior is consistent across all handles:
        - save(): stage to Plan by default (preview-friendly)
        - save(stage=False): write directly to original file
        - save(path=...): write to a different target (defaults to direct write)
        - save(path=..., stage=True): stage write to a different target
        """
        self._ensure_loaded()

        if stage is None:
            stage = path is None

        target_path = Path(path) if path else self.path

        if stage:
            from .plan import plan

            plan.stage(target_path, self._get_serialized_content())
        else:
            target_file = File(str(target_path))
            # Only create parents for local paths
            if not target_file.is_remote:
                target_file.path.parent.mkdir(parents=True, exist_ok=True)
            target_file.write_text(self._get_serialized_content(), encoding="utf-8")
