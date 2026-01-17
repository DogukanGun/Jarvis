"""
Tests for password_crack_john tool.

Prerequisites:
    1. Compile John the Ripper:
       cd external_sources/john/src && ./configure && make -s clean && make -sj4

    OR install via package manager:
       brew install john  # macOS
       apt install john   # Ubuntu

Usage:
    pytest test_password_crack_john.py -v
    pytest test_password_crack_john.py -v -k "test_client"  # Run specific tests
"""

import os
import sys
import pytest
import shutil

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from app.graphs.hacker_graph.tools.password_crack_john import (
    JohnClient,
    john_crack,
    john_show,
    john_convert,
    JOHN_RUN_PATH,
)


# Test fixtures paths
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
HASH_FILE = os.path.join(FIXTURES_DIR, "hashes.txt")
WORDLIST_FILE = os.path.join(FIXTURES_DIR, "wordlist.txt")


# --- Fixtures ---

@pytest.fixture(scope="module")
def john_available() -> bool:
    """Check if John binary is available."""
    # Check local build
    local_john = os.path.join(JOHN_RUN_PATH, "john")
    if os.path.isfile(local_john) and os.access(local_john, os.X_OK):
        return True

    # Check system PATH
    if shutil.which("john"):
        return True

    return False


@pytest.fixture(scope="module")
def john_client(john_available: bool):
    """Create JohnClient instance if john is available."""
    if not john_available:
        pytest.skip("John the Ripper binary not available")
    return JohnClient()


@pytest.fixture
def hash_file() -> str:
    """Path to test hash file."""
    assert os.path.exists(HASH_FILE), f"Hash file not found: {HASH_FILE}"
    return HASH_FILE


@pytest.fixture
def wordlist_file() -> str:
    """Path to test wordlist."""
    assert os.path.exists(WORDLIST_FILE), f"Wordlist not found: {WORDLIST_FILE}"
    return WORDLIST_FILE


# --- JohnClient Tests ---

class TestJohnClient:
    """Tests for JohnClient class."""

    def test_client_init_no_binary(self):
        """Test client initialization when binary not found."""
        # Test with explicit nonexistent binary - should use it directly
        client = JohnClient(john_binary="/nonexistent/path/john")
        # The binary path is set but won't work when called
        assert client.john_binary == "/nonexistent/path/john"

    def test_is_available(self, john_available: bool):
        """Test is_available method."""
        if john_available:
            client = JohnClient()
            assert client.is_available() is True

    def test_list_converters(self):
        """Test listing available converters."""
        # This doesn't need the binary, just checks run directory
        if not os.path.exists(JOHN_RUN_PATH):
            pytest.skip("John run directory not found")

        converters = []
        for f in os.listdir(JOHN_RUN_PATH):
            if "2john" in f and (f.endswith(".py") or f.endswith(".pl")):
                converters.append(f.rsplit(".", 1)[0])

        assert len(converters) > 0
        assert "ssh2john" in converters

    def test_get_version(self, john_client: JohnClient):
        """Test getting john version."""
        version = john_client.get_version()
        assert version is not None
        assert len(version) > 0

    def test_list_formats(self, john_client: JohnClient):
        """Test listing supported hash formats."""
        formats = john_client.list_formats()
        assert isinstance(formats, list)
        assert len(formats) > 0
        # Common formats should be present
        format_str = " ".join(formats).lower()
        assert "md5" in format_str or "raw-md5" in format_str


class TestJohnClientCracking:
    """Tests for JohnClient cracking functionality."""

    @pytest.mark.slow
    def test_crack_md5_hashes(self, john_client: JohnClient, hash_file: str, wordlist_file: str):
        """Test cracking MD5 hashes with wordlist."""
        result = john_client.crack(
            hash_file=hash_file,
            wordlist=wordlist_file,
            format="raw-md5",
            max_run_time=30
        )

        assert "returncode" in result
        assert "cracked" in result
        # We expect some passwords to be cracked
        assert isinstance(result["cracked"], list)

    @pytest.mark.slow
    def test_show_cracked(self, john_client: JohnClient, hash_file: str):
        """Test showing cracked passwords."""
        cracked = john_client.show(hash_file, format="raw-md5")
        assert isinstance(cracked, list)
        # Each entry should have user and password
        for entry in cracked:
            assert "user" in entry
            assert "password" in entry


# --- Tool Function Tests ---

class TestJohnCrackTool:
    """Tests for john_crack LangChain tool."""

    def test_tool_has_required_attributes(self):
        """Test tool has required LangChain attributes."""
        assert hasattr(john_crack, "name")
        assert hasattr(john_crack, "description")
        assert hasattr(john_crack, "invoke")
        assert john_crack.name == "john_crack"

    def test_tool_with_nonexistent_file(self):
        """Test tool with nonexistent hash file."""
        result = john_crack.invoke({
            "hash_file": "/nonexistent/hashes.txt",
            "mode": "wordlist"
        })
        # Should handle gracefully
        assert isinstance(result, str)
        # Check for various error indicators
        result_lower = result.lower()
        assert any(x in result_lower for x in ["error", "no such file", "not found"])

    @pytest.mark.slow
    def test_tool_crack_with_wordlist(self, john_available: bool, hash_file: str, wordlist_file: str):
        """Test tool cracking with wordlist."""
        if not john_available:
            pytest.skip("John binary not available")

        result = john_crack.invoke({
            "hash_file": hash_file,
            "wordlist": wordlist_file,
            "format": "raw-md5",
            "mode": "wordlist",
            "max_run_time": 30
        })

        assert isinstance(result, str)
        # Should not have critical errors
        assert "Error:" not in result or "timed out" in result


class TestJohnShowTool:
    """Tests for john_show LangChain tool."""

    def test_tool_has_required_attributes(self):
        """Test tool has required LangChain attributes."""
        assert hasattr(john_show, "name")
        assert hasattr(john_show, "description")
        assert hasattr(john_show, "invoke")
        assert john_show.name == "john_show"

    def test_tool_with_nonexistent_file(self):
        """Test tool with nonexistent hash file."""
        result = john_show.invoke({
            "hash_file": "/nonexistent/hashes.txt"
        })
        assert isinstance(result, str)

    def test_tool_show_cracked(self, john_available: bool, hash_file: str):
        """Test showing cracked passwords."""
        if not john_available:
            pytest.skip("John binary not available")

        result = john_show.invoke({
            "hash_file": hash_file,
            "format": "raw-md5"
        })

        assert isinstance(result, str)


class TestJohnConvertTool:
    """Tests for john_convert LangChain tool."""

    def test_tool_has_required_attributes(self):
        """Test tool has required LangChain attributes."""
        assert hasattr(john_convert, "name")
        assert hasattr(john_convert, "description")
        assert hasattr(john_convert, "invoke")
        assert john_convert.name == "john_convert"

    def test_tool_with_nonexistent_converter(self):
        """Test tool with nonexistent converter."""
        result = john_convert.invoke({
            "input_file": "/some/file.txt",
            "converter": "nonexistent2john"
        })
        assert isinstance(result, str)
        assert "not found" in result.lower() or "error" in result.lower()

    def test_tool_with_nonexistent_input_file(self):
        """Test tool with nonexistent input file."""
        result = john_convert.invoke({
            "input_file": "/nonexistent/id_rsa",
            "converter": "ssh"
        })
        assert isinstance(result, str)


# --- Input Validation Tests ---

class TestInputValidation:
    """Tests for input validation."""

    def test_valid_mode_validation(self):
        """Test mode parameter validation."""
        from app.graphs.hacker_graph.tools.password_crack_john import JohnCrackInput

        valid_modes = ["wordlist", "incremental", "single", "mask"]
        for mode in valid_modes:
            input_data = JohnCrackInput(hash_file="/test/hashes.txt", mode=mode)
            assert input_data.mode == mode

    def test_invalid_mode_validation(self):
        """Test mode validation fails for invalid modes."""
        from app.graphs.hacker_graph.tools.password_crack_john import JohnCrackInput

        with pytest.raises(ValueError):
            JohnCrackInput(hash_file="/test/hashes.txt", mode="invalid_mode")

    def test_valid_charset_validation(self):
        """Test incremental_charset validation."""
        from app.graphs.hacker_graph.tools.password_crack_john import JohnCrackInput

        valid_charsets = ["ASCII", "Alnum", "Alpha", "Digits", "LowerNum", "UpperNum"]
        for charset in valid_charsets:
            input_data = JohnCrackInput(
                hash_file="/test/hashes.txt",
                incremental_charset=charset
            )
            assert input_data.incremental_charset == charset

    def test_invalid_charset_validation(self):
        """Test charset validation fails for invalid charsets."""
        from app.graphs.hacker_graph.tools.password_crack_john import JohnCrackInput

        with pytest.raises(ValueError):
            JohnCrackInput(
                hash_file="/test/hashes.txt",
                incremental_charset="InvalidCharset"
            )


# --- Converter Tests ---

class TestConverters:
    """Tests for john converters."""

    def test_converter_scripts_exist(self):
        """Test that converter scripts exist."""
        if not os.path.exists(JOHN_RUN_PATH):
            pytest.skip("John run directory not found")

        # These converters exist as .py scripts
        expected_converters = [
            "ssh2john.py",
            "pdf2john.py",  # Also has .pl version
            "bitcoin2john.py",
            "ansible2john.py",
        ]

        for converter in expected_converters:
            converter_path = os.path.join(JOHN_RUN_PATH, converter)
            # Some might be .pl instead of .py
            pl_path = converter_path.replace(".py", ".pl")
            assert os.path.exists(converter_path) or os.path.exists(pl_path), \
                f"Converter not found: {converter}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
