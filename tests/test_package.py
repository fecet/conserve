"""Tests for Package module."""

import pytest
from conserve import Package


def test_package_creation_short_format():
    """Test Package creation with short PURL format."""
    pkg = Package("pypi/requests")
    assert pkg.version is None


def test_package_creation_with_version():
    """Test Package creation with version in PURL."""
    pkg = Package("pypi/requests@2.31.0")
    assert pkg.version == "2.31.0"


def test_package_creation_full_purl():
    """Test Package creation with full PURL format."""
    pkg = Package("pkg:pypi/requests@2.31.0")
    assert pkg.version == "2.31.0"


def test_package_invalid_type():
    """Test Package creation with unsupported type raises on method call."""
    pkg = Package("invalid-type/package")
    # Error should raise when calling methods that need client
    with pytest.raises(ValueError, match="Unsupported package type"):
        pkg.latest()


def test_package_invalid_purl():
    """Test Package creation with invalid PURL format."""
    with pytest.raises(ValueError, match="Invalid PURL format"):
        Package("")  # Empty string will become "pkg:" which is invalid


@pytest.mark.integration
def test_package_latest_pypi():
    """Test getting latest PyPI package version."""
    pkg = Package("pypi/requests")
    latest = pkg.latest()
    assert latest.version is not None
    assert latest.version != ""


@pytest.mark.integration
def test_package_info():
    """Test getting package metadata."""
    pkg = Package("pypi/requests@2.31.0")
    info = pkg.info()
    assert "version" in info
    assert info["version"] == "2.31.0"


@pytest.mark.integration
def test_package_info_no_version():
    """Test getting package info without version (auto-fetches latest)."""
    pkg = Package("pypi/requests")
    info = pkg.info()
    assert "version" in info
    assert info["version"] is not None
    # Should have detailed version info (not just version list)
    assert "licenses" in info or "published_at" in info


@pytest.mark.integration
def test_package_latest_npm():
    """Test getting latest npm package version."""
    pkg = Package("npm/lodash")
    latest = pkg.latest()
    assert latest.version is not None


def test_package_creation_github():
    """Test Package creation with GitHub PURL format."""
    pkg = Package("github/pytorch/pytorch")
    assert pkg.version is None


def test_package_creation_github_with_version():
    """Test Package creation with GitHub PURL and version."""
    pkg = Package("github/pytorch/pytorch@v2.0.0")
    assert pkg.version == "v2.0.0"


@pytest.mark.integration
def test_package_latest_github():
    """Test getting latest GitHub release version."""
    pkg = Package("github/pytorch/pytorch")
    latest = pkg.latest()
    assert latest.version is not None
    assert latest.version.startswith("v")


@pytest.mark.integration
def test_package_info_github():
    """Test getting GitHub repository metadata (auto-fetches latest)."""
    pkg = Package("github/pytorch/pytorch")
    info = pkg.info()
    assert "version" in info
    assert info["version"] is not None
    # Should have release-specific info
    assert "tag_name" in info or "published_at" in info


@pytest.mark.integration
def test_package_info_github_with_version():
    """Test getting specific GitHub release info."""
    pkg = Package("github/pytorch/pytorch@v2.0.0")
    info = pkg.info()
    assert "tag_name" in info
    assert info["tag_name"] == "v2.0.0"
    assert "assets" in info
