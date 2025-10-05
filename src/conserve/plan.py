"""Plan module for change management."""

from pathlib import Path
from uuid import uuid4
import difflib
from .file import File


class Plan:
    """Simplified change plan manager - Handles provide path and content only."""

    def __init__(self):
        # Real path -> memory file mapping
        self._staging_map: dict[Path, File] = {}
        # Record original content for diff
        self._original_contents: dict[Path, str | None] = {}

    def stage(self, real_path: Path, content: str) -> None:
        """Handle calls this method to stage content.

        - Handle only needs to provide: target path + serialized content
        - Plan manages memory files and mapping relationships
        """
        # Record original content (on first staging)
        if real_path not in self._original_contents:
            real_file = File(str(real_path))
            self._original_contents[real_path] = real_file.read_text() if real_file.exists() else None

        # Create memory file and stage content
        memory_path = f"memory://staging/{uuid4()}/{real_path.name}"
        memory_file = File(memory_path)
        memory_file.write_text(content)
        self._staging_map[real_path] = memory_file

    def get_diff_summary(self) -> str:
        """Generate diff summary for all changes."""
        diffs = []
        for real_path, memory_file in self._staging_map.items():
            original = self._original_contents.get(real_path, "")
            modified = memory_file.read_text()
            if original != modified:
                diff = difflib.unified_diff(
                    (original or "").splitlines(keepends=True),
                    modified.splitlines(keepends=True),
                    fromfile=str(real_path),
                    tofile=str(real_path),
                )
                diffs.append("".join(diff))
        return "\n".join(diffs)

    def preview(self) -> dict[Path, str]:
        """Preview content to be written."""
        return {real_path: memory_file.read_text() for real_path, memory_file in self._staging_map.items()}

    def commit(self) -> None:
        """Batch commit all staged changes."""
        # Write directly, using File abstraction
        for real_path, memory_file in self._staging_map.items():
            File(str(real_path)).write_text(memory_file.read_text())
        self._staging_map.clear()
        self._original_contents.clear()

    def rollback(self) -> None:
        """Clear staged changes."""
        self._staging_map.clear()
        self._original_contents.clear()

    def clear(self) -> None:
        """Clear all state (for task isolation)."""
        self._staging_map.clear()
        self._original_contents.clear()


# Global singleton Plan instance
# Safe under sequential execution and usage conventions
plan = Plan()
