import os
import subprocess
import shutil
import tempfile
from typing import Optional, List, Dict, Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator


JOHN_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "external_sources", "john"
)
JOHN_RUN_PATH = os.path.join(JOHN_PATH, "run")


class JohnClient:
    """
    CLI wrapper client for John the Ripper.

    Usage:
        client = JohnClient()

        # Crack password hashes
        result = client.crack("hashes.txt", wordlist="/path/to/wordlist.txt")

        # Show cracked passwords
        cracked = client.show("hashes.txt")

        # Convert SSH key to john format
        john_hash = client.convert_ssh_key("/path/to/id_rsa")
    """

    def __init__(self, john_binary: Optional[str] = None):
        """
        Initialize JohnClient.

        Args:
            john_binary: Path to john binary. If None, searches in:
                        1. external_sources/john/run/john
                        2. System PATH
        """
        self.john_binary = john_binary or self._find_john_binary()
        self.run_path = JOHN_RUN_PATH

    def _find_john_binary(self) -> str:
        """Find john binary in known locations."""
        # Check compiled binary in repo
        local_john = os.path.join(JOHN_RUN_PATH, "john")
        if os.path.isfile(local_john) and os.access(local_john, os.X_OK):
            return local_john

        # Check system PATH
        system_john = shutil.which("john")
        if system_john:
            return system_john

        raise FileNotFoundError(
            "John the Ripper binary not found. Either:\n"
            "1. Compile it: cd external_sources/john/src && ./configure && make\n"
            "2. Install via package manager: brew install john / apt install john"
        )

    def _run_john(
        self,
        args: List[str],
        timeout: int = 300,
        cwd: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """Run john with given arguments."""
        cmd = [self.john_binary] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or self.run_path,
            check=False
        )

    def _run_converter(
        self,
        script: str,
        args: List[str],
        timeout: int = 60
    ) -> subprocess.CompletedProcess:
        """Run a *2john converter script."""
        script_path = os.path.join(self.run_path, script)
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"Converter script not found: {script}")

        cmd = ["python", script_path] + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=self.run_path,
            check=False
        )

    def is_available(self) -> bool:
        """Check if john binary is available."""
        try:
            self._find_john_binary()
            return True
        except FileNotFoundError:
            return False

    def get_version(self) -> str:
        """Get john version string."""
        result = self._run_john(["--version"], timeout=10)
        return result.stdout.strip() or result.stderr.strip()

    def list_formats(self) -> List[str]:
        """List all supported hash formats."""
        result = self._run_john(["--list=formats"], timeout=30)
        output = result.stdout + result.stderr
        # Parse format list (comma or newline separated)
        formats = []
        for line in output.split("\n"):
            formats.extend([f.strip() for f in line.split(",") if f.strip()])
        return formats

    def detect_format(self, hash_file: str) -> List[str]:
        """Auto-detect hash format from file."""
        result = self._run_john([hash_file, "--show=formats"], timeout=30)
        output = result.stdout + result.stderr
        # Extract detected formats
        formats = []
        for line in output.split("\n"):
            if line.strip() and not line.startswith("Warning"):
                formats.append(line.strip())
        return formats

    def crack(
        self,
        hash_file: str,
        wordlist: Optional[str] = None,
        format: Optional[str] = None,
        rules: Optional[str] = None,
        incremental: Optional[str] = None,
        mask: Optional[str] = None,
        session: Optional[str] = None,
        fork: int = 1,
        max_run_time: int = 300,
        extra_args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Crack password hashes.

        Args:
            hash_file: Path to file containing hashes
            wordlist: Path to wordlist file
            format: Hash format (e.g., 'raw-md5', 'bcrypt', 'sha512crypt')
            rules: Mangling rules section name
            incremental: Incremental mode charset (e.g., 'ASCII', 'Alnum')
            mask: Mask pattern (e.g., '?u?l?l?l?d?d')
            session: Session name for restore capability
            fork: Number of parallel processes
            max_run_time: Maximum runtime in seconds
            extra_args: Additional john arguments

        Returns:
            Dict with 'stdout', 'stderr', 'returncode', 'cracked' keys
        """
        args = [hash_file]

        if wordlist:
            args.append(f"--wordlist={wordlist}")
        if format:
            args.append(f"--format={format}")
        if rules:
            args.append(f"--rules={rules}")
        if incremental:
            args.append(f"--incremental={incremental}")
        if mask:
            args.append(f"--mask={mask}")
        if session:
            args.append(f"--session={session}")
        if fork > 1:
            args.append(f"--fork={fork}")
        if extra_args:
            args.extend(extra_args)

        result = self._run_john(args, timeout=max_run_time)

        # Get cracked passwords
        cracked = self.show(hash_file, format=format)

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "cracked": cracked
        }

    def show(
        self,
        hash_file: str,
        format: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Show cracked passwords.

        Args:
            hash_file: Path to hash file
            format: Hash format

        Returns:
            List of dicts with 'user' and 'password' keys
        """
        args = ["--show", hash_file]
        if format:
            args.append(f"--format={format}")

        result = self._run_john(args, timeout=30)
        output = result.stdout

        cracked = []
        for line in output.split("\n"):
            if ":" in line and not line.startswith("Warning"):
                parts = line.split(":")
                if len(parts) >= 2:
                    cracked.append({
                        "user": parts[0],
                        "password": parts[1]
                    })

        return cracked

    def restore(self, session: str) -> Dict[str, Any]:
        """Restore a previous cracking session."""
        result = self._run_john([f"--restore={session}"], timeout=300)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    def convert_ssh_key(self, key_file: str) -> str:
        """Convert SSH private key to john format."""
        result = self._run_converter("ssh2john.py", [key_file])
        if result.returncode != 0:
            raise RuntimeError(f"ssh2john failed: {result.stderr}")
        return result.stdout.strip()

    def convert_zip(self, zip_file: str) -> str:
        """Convert password-protected ZIP to john format."""
        result = self._run_converter("zip2john.py", [zip_file])
        if result.returncode != 0:
            # Try perl version
            result = self._run_converter("zip2john", [zip_file])
        return result.stdout.strip()

    def convert_pdf(self, pdf_file: str) -> str:
        """Convert password-protected PDF to john format."""
        result = self._run_converter("pdf2john.py", [pdf_file])
        if result.returncode != 0:
            raise RuntimeError(f"pdf2john failed: {result.stderr}")
        return result.stdout.strip()

    def convert_keepass(self, kdbx_file: str) -> str:
        """Convert KeePass database to john format."""
        result = self._run_converter("keepass2john.py", [kdbx_file])
        if result.returncode != 0:
            raise RuntimeError(f"keepass2john failed: {result.stderr}")
        return result.stdout.strip()

    def convert_generic(self, converter: str, input_file: str) -> str:
        """
        Run any *2john converter.

        Args:
            converter: Converter name (e.g., 'bitcoin2john', 'office2john')
            input_file: Input file to convert

        Returns:
            John-compatible hash string
        """
        # Try .py first, then without extension
        for ext in [".py", ".pl", ""]:
            script = converter + ext
            script_path = os.path.join(self.run_path, script)
            if os.path.isfile(script_path):
                result = self._run_converter(script, [input_file])
                if result.returncode == 0:
                    return result.stdout.strip()
                raise RuntimeError(f"{script} failed: {result.stderr}")

        raise FileNotFoundError(f"Converter not found: {converter}")

    def list_converters(self) -> List[str]:
        """List available *2john converters."""
        converters = []
        for f in os.listdir(self.run_path):
            if "2john" in f and (f.endswith(".py") or f.endswith(".pl")):
                name = f.rsplit(".", 1)[0]
                converters.append(name)
        return sorted(set(converters))


# --- Pydantic Input Schemas ---

class JohnCrackInput(BaseModel):
    hash_file: str = Field(
        ...,
        description="Path to file containing password hashes"
    )
    wordlist: Optional[str] = Field(
        None,
        description="Path to wordlist file for dictionary attack"
    )
    format: Optional[str] = Field(
        None,
        description="Hash format (e.g., 'raw-md5', 'bcrypt', 'sha512crypt'). Auto-detected if not specified."
    )
    mode: str = Field(
        "wordlist",
        description="Attack mode: 'wordlist', 'incremental', 'single', or 'mask'"
    )
    incremental_charset: str = Field(
        "ASCII",
        description="Charset for incremental mode: 'ASCII', 'Alnum', 'Alpha', 'Digits'"
    )
    mask: Optional[str] = Field(
        None,
        description="Mask pattern for mask mode (e.g., '?u?l?l?l?d?d' = Uppercase+3lower+2digits)"
    )
    max_run_time: int = Field(
        120,
        description="Maximum runtime in seconds"
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid = {"wordlist", "incremental", "single", "mask"}
        if v not in valid:
            raise ValueError(f"mode must be one of {valid}")
        return v

    @field_validator("incremental_charset")
    @classmethod
    def validate_charset(cls, v: str) -> str:
        valid = {"ASCII", "Alnum", "Alpha", "Digits", "LowerNum", "UpperNum"}
        if v not in valid:
            raise ValueError(f"incremental_charset must be one of {valid}")
        return v


class JohnShowInput(BaseModel):
    hash_file: str = Field(
        ...,
        description="Path to file containing password hashes"
    )
    format: Optional[str] = Field(
        None,
        description="Hash format (optional, auto-detected)"
    )


class JohnConvertInput(BaseModel):
    input_file: str = Field(
        ...,
        description="Path to file to convert (SSH key, ZIP, PDF, etc.)"
    )
    converter: str = Field(
        ...,
        description="Converter to use: 'ssh', 'zip', 'pdf', 'keepass', 'office', 'bitcoin', etc."
    )


# --- LangChain Tools ---

def _format_output(result: Dict[str, Any]) -> str:
    """Format john output for readability."""
    lines = []

    if result.get("cracked"):
        lines.append("=== CRACKED PASSWORDS ===")
        for entry in result["cracked"]:
            lines.append(f"  {entry['user']}:{entry['password']}")
        lines.append("")

    stdout = result.get("stdout", "").strip()
    stderr = result.get("stderr", "").strip()

    if stdout:
        lines.append("=== OUTPUT ===")
        lines.append(stdout[:4000])

    if stderr and "Warning" not in stderr:
        lines.append("=== ERRORS ===")
        lines.append(stderr[:1000])

    output = "\n".join(lines) if lines else "No output"
    if len(output) > 8000:
        output = output[:8000] + "\n...[truncated]..."
    return output


@tool("john_crack", args_schema=JohnCrackInput)
def john_crack(
    hash_file: str,
    wordlist: Optional[str] = None,
    format: Optional[str] = None,
    mode: str = "wordlist",
    incremental_charset: str = "ASCII",
    mask: Optional[str] = None,
    max_run_time: int = 120
) -> str:
    """
    Crack password hashes using John the Ripper.

    Supports multiple attack modes:
    - wordlist: Dictionary attack with optional mangling rules
    - incremental: Brute force with charset frequency analysis
    - single: Uses login names and GECOS info
    - mask: Pattern-based (e.g., ?u?l?l?d for Upper+2lower+digit)

    Returns cracked passwords and attack progress.
    """
    try:
        client = JohnClient()
    except FileNotFoundError as e:
        return f"Error: {e}"

    try:
        # Build attack parameters based on mode
        kwargs = {
            "hash_file": hash_file,
            "format": format,
            "max_run_time": max_run_time
        }

        if mode == "wordlist":
            if wordlist:
                kwargs["wordlist"] = wordlist
            kwargs["rules"] = "Wordlist"
        elif mode == "incremental":
            kwargs["incremental"] = incremental_charset
        elif mode == "single":
            kwargs["extra_args"] = ["--single"]
        elif mode == "mask":
            if mask:
                kwargs["mask"] = mask
            else:
                kwargs["mask"] = "?a?a?a?a?a?a"  # Default 6-char all printable

        result = client.crack(**kwargs)
        return _format_output(result)

    except subprocess.TimeoutExpired:
        return f"Cracking timed out after {max_run_time}s. Use --restore to continue."
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


@tool("john_show", args_schema=JohnShowInput)
def john_show(hash_file: str, format: Optional[str] = None) -> str:
    """
    Show passwords cracked by John the Ripper.

    Reads from John's pot file to display previously cracked passwords
    for the given hash file.
    """
    try:
        client = JohnClient()
    except FileNotFoundError as e:
        return f"Error: {e}"

    try:
        cracked = client.show(hash_file, format=format)

        if not cracked:
            return "No cracked passwords found for this hash file."

        lines = ["=== CRACKED PASSWORDS ==="]
        for entry in cracked:
            lines.append(f"  {entry['user']}:{entry['password']}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


@tool("john_convert", args_schema=JohnConvertInput)
def john_convert(input_file: str, converter: str) -> str:
    """
    Convert various file formats to John-compatible hash format.

    Supported converters include:
    - ssh: SSH private keys
    - zip: Password-protected ZIP files
    - pdf: Password-protected PDFs
    - keepass: KeePass database files
    - office: Microsoft Office documents
    - bitcoin/ethereum: Crypto wallet files
    - 7z, rar: Archive files
    - And 100+ more (use 'john_list_converters' to see all)

    Returns the hash string ready for cracking with john_crack.
    """
    try:
        client = JohnClient()
    except FileNotFoundError as e:
        return f"Error: {e}"

    # Map short names to full converter names
    converter_map = {
        "ssh": "ssh2john",
        "zip": "zip2john",
        "pdf": "pdf2john",
        "keepass": "keepass2john",
        "office": "office2john",
        "bitcoin": "bitcoin2john",
        "ethereum": "ethereum2john",
        "7z": "7z2john",
        "rar": "rar2john",
        "gpg": "gpg2john",
        "pgp": "gpg2john",
        "ansible": "ansible2john",
        "bitlocker": "bitlocker2john",
        "veracrypt": "veracrypt2john",
        "truecrypt": "truecrypt2john",
        "lastpass": "lastpass2john",
        "1password": "1password2john",
        "bitwarden": "bitwarden2john",
        "dmg": "dmg2john",
    }

    full_converter = converter_map.get(converter.lower(), converter)
    if not full_converter.endswith("2john"):
        full_converter = full_converter + "2john"

    try:
        hash_output = client.convert_generic(full_converter, input_file)

        if not hash_output:
            return f"No hash extracted from {input_file}"

        lines = [
            f"=== EXTRACTED HASH ({full_converter}) ===",
            hash_output,
            "",
            "Use john_crack with this hash to attempt cracking."
        ]
        return "\n".join(lines)

    except FileNotFoundError:
        available = client.list_converters()
        return (
            f"Converter '{full_converter}' not found.\n"
            f"Available converters: {', '.join(available[:20])}..."
        )
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
