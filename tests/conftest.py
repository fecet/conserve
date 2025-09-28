"""Pytest configuration and fixtures"""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def workspace():
    """Create a temporary workspace directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)
