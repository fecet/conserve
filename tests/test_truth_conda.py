"""Tests for truth.conda module."""

import pytest
import json
from unittest.mock import patch, MagicMock
from conserve import truth
from conserve.truth.conda import normalize_pypi_name


class TestCondaMapping:
    """Test Conda-PyPI mapping functionality."""

    @pytest.fixture
    def mock_mapping_data(self):
        """Sample mapping data for testing."""
        return {
            "pytorch": "torch",
            "pillow": "Pillow",
            "beautifulsoup4": "beautifulsoup4",
            "numpy": "numpy",
            "pytorch-cpu": "torch",
            "msgpack-python": "msgpack",
            "pytables": "tables",
        }

    @pytest.fixture
    def mapper_with_mock_data(self, tmp_path, mock_mapping_data):
        """Create a mapper with mocked data."""
        mapper = truth.conda.CondaMapping(cache_dir=tmp_path)
        mapper._mapping_data = mock_mapping_data
        return mapper

    def test_conda_to_pypi(self, mapper_with_mock_data):
        """Test Conda to PyPI name conversion."""
        mapper = mapper_with_mock_data

        # Direct mappings
        assert mapper.conda_to_pypi("pytorch") == "torch"
        assert mapper.conda_to_pypi("pillow") == "Pillow"
        assert mapper.conda_to_pypi("numpy") == "numpy"

        # Unknown package
        assert mapper.conda_to_pypi("unknown-package") is None

    def test_pypi_to_conda(self, mapper_with_mock_data):
        """Test PyPI to Conda name conversion."""
        mapper = mapper_with_mock_data

        # Reverse mappings
        assert mapper.pypi_to_conda("torch") == "pytorch"  # First occurrence wins
        assert mapper.pypi_to_conda("Pillow") == "pillow"
        assert mapper.pypi_to_conda("numpy") == "numpy"
        assert mapper.pypi_to_conda("msgpack") == "msgpack-python"

        # Unknown package
        assert mapper.pypi_to_conda("unknown-package") is None

    def test_search(self, mapper_with_mock_data):
        """Test searching for mappings."""
        mapper = mapper_with_mock_data

        # Search for "torch"
        results = mapper.search("torch")
        assert "pytorch" in results
        assert "pytorch-cpu" in results
        assert results["pytorch"] == "torch"

        # Search for "msg"
        results = mapper.search("msg")
        assert "msgpack-python" in results
        assert results["msgpack-python"] == "msgpack"

        # No matches
        results = mapper.search("xyz123")
        assert len(results) == 0

    def test_get_all(self, mapper_with_mock_data, mock_mapping_data):
        """Test getting all mappings."""
        mapper = mapper_with_mock_data
        all_mappings = mapper.get_all()

        assert all_mappings == mock_mapping_data
        # Ensure it's a copy
        all_mappings["test"] = "value"
        assert "test" not in mapper._mapping_data

    def test_cache_functionality(self, tmp_path, mock_mapping_data):
        """Test caching of mapping data."""
        cache_dir = tmp_path / "test_cache"
        mapper = truth.conda.CondaMapping(cache_dir=cache_dir)

        # Mock the URL fetch
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(mock_mapping_data).encode()
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # First fetch should hit the network
            mapper._fetch_mapping()
            assert mock_urlopen.called
            assert (cache_dir / "conda_pypi_mapping.json").exists()

            # Second fetch should use cache
            mock_urlopen.reset_mock()
            mapper2 = truth.conda.CondaMapping(cache_dir=cache_dir)
            mapper2._fetch_mapping()
            assert not mock_urlopen.called
            assert mapper2._mapping_data == mock_mapping_data

    def test_clear_cache(self, tmp_path, mock_mapping_data):
        """Test cache clearing."""
        mapper = truth.conda.CondaMapping(cache_dir=tmp_path)
        cache_file = tmp_path / "conda_pypi_mapping.json"

        # Create cache file
        with open(cache_file, "w") as f:
            json.dump(mock_mapping_data, f)

        mapper._mapping_data = mock_mapping_data
        mapper._reverse_mapping = {"test": "value"}

        # Clear cache
        mapper.clear_cache()

        assert not cache_file.exists()
        assert mapper._mapping_data is None
        assert mapper._reverse_mapping is None


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    @pytest.fixture
    def mock_mapping_data(self):
        """Sample mapping data for testing."""
        return {
            "pytorch": "torch",
            "pillow": "Pillow",
            "beautifulsoup4": "beautifulsoup4",
            "numpy": "numpy",
            "pytorch-cpu": "torch",
            "msgpack-python": "msgpack",
            "pytables": "tables",
        }

    @pytest.fixture(autouse=True)
    def mock_mapper(self, mock_mapping_data):
        """Mock the default mapper."""
        with patch("conserve.truth.conda._get_mapper") as mock_get:
            mapper = MagicMock()
            mapper.conda_to_pypi.side_effect = lambda x: mock_mapping_data.get(x)
            mapper.pypi_to_conda.side_effect = lambda x: {
                "torch": "pytorch",
                "Pillow": "pillow",
                "numpy": "numpy",
                "msgpack": "msgpack-python",
            }.get(x)
            mapper.search.side_effect = lambda p: {
                k: v for k, v in mock_mapping_data.items() if p.lower() in k.lower() or p.lower() in v.lower()
            }
            mock_get.return_value = mapper
            yield mapper

    def test_to_pypi_single(self):
        """Test to_pypi with single package name."""
        assert truth.conda.to_pypi("pytorch") == "torch"
        assert truth.conda.to_pypi("numpy") == "numpy"
        assert truth.conda.to_pypi("unknown") is None

    def test_to_pypi_list(self):
        """Test to_pypi with list of package names."""
        results = truth.conda.to_pypi(["pytorch", "numpy", "pillow", "unknown"])
        assert results == ["torch", "numpy", "Pillow", None]

    def test_to_conda_single(self):
        """Test to_conda with single package name."""
        assert truth.conda.to_conda("torch") == "pytorch"
        assert truth.conda.to_conda("numpy") == "numpy"
        assert truth.conda.to_conda("unknown") is None

    def test_to_conda_list(self):
        """Test to_conda with list of package names."""
        results = truth.conda.to_conda(["torch", "numpy", "Pillow", "unknown"])
        assert results == ["pytorch", "numpy", "pillow", None]

    def test_search_function(self, mock_mapping_data):
        """Test search function."""
        results = truth.conda.search("torch")
        assert "pytorch" in results
        assert results["pytorch"] == "torch"

    def test_mapping_alias(self):
        """Test mapping function (alias for to_pypi)."""
        assert truth.conda.mapping("pytorch") == "torch"

    def test_reverse_mapping_alias(self):
        """Test reverse_mapping function (alias for to_conda)."""
        assert truth.conda.reverse_mapping("torch") == "pytorch"


class TestPEP503Normalization:
    """Test PEP 503 normalization functionality."""

    def test_normalize_pypi_name(self):
        """Test PEP 503 normalization of PyPI package names."""
        test_cases = [
            # (input, expected)
            ("ruamel.yaml", "ruamel-yaml"),
            ("ruamel_yaml", "ruamel-yaml"),
            ("Pillow", "pillow"),
            ("msgpack-python", "msgpack-python"),
            ("beautifulsoup4", "beautifulsoup4"),
            ("my.package_name", "my-package-name"),
            ("My__Package..Name", "my-package-name"),
            ("package---name", "package-name"),
        ]

        for input_name, expected in test_cases:
            result = normalize_pypi_name(input_name)
            assert result == expected, f"Failed for {input_name}: got {result}, expected {expected}"

    @pytest.fixture
    def mock_mapping_with_normalized(self):
        """Mock mapping data with normalized names."""
        return {
            "pytorch": "torch",
            "pillow": "pillow",
            "ruamel.yaml": "ruamel-yaml",  # Normalized form in mapping
            "beautifulsoup4": "beautifulsoup4",
        }

    def test_pypi_to_conda_with_normalization(self, tmp_path, mock_mapping_with_normalized):
        """Test that pypi_to_conda handles normalized names correctly."""
        mapper = truth.conda.CondaMapping(cache_dir=tmp_path)
        mapper._mapping_data = mock_mapping_with_normalized

        # Test with various forms of ruamel.yaml
        assert mapper.pypi_to_conda("ruamel.yaml") == "ruamel.yaml"  # Should find via normalization
        assert mapper.pypi_to_conda("ruamel_yaml") == "ruamel.yaml"  # Should find via normalization
        assert mapper.pypi_to_conda("ruamel-yaml") == "ruamel.yaml"  # Direct match after normalization

        # Test case sensitivity
        assert mapper.pypi_to_conda("Pillow") == "pillow"
        assert mapper.pypi_to_conda("PILLOW") == "pillow"
        assert mapper.pypi_to_conda("pillow") == "pillow"
