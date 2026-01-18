"""
OSINT tool wrapper for ReconSpider.

Provides clean API access to ReconSpider's OSINT capabilities:
- IP address lookup (geolocation, ISP, org)
- Domain reconnaissance
- Phone number lookup
- Honeypot detection
- Shodan integration
"""

import sys
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

# Add reconspider to path
RECONSPIDER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "external_sources", "reconspider"
)
sys.path.insert(0, RECONSPIDER_PATH)


@dataclass
class OSINTResult:
    """Result from OSINT lookup."""
    success: bool = False
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class OSINTClient:
    """
    Client for OSINT operations using various APIs.

    Usage:
        client = OSINTClient(shodan_api_key="your_key")
        result = client.ip_lookup("8.8.8.8")
        print(result.data)
    """

    def __init__(
        self,
        shodan_api_key: Optional[str] = None,
        ipstack_api_key: Optional[str] = None,
        numverify_api_key: Optional[str] = None
    ):
        self.shodan_api_key = shodan_api_key or self._load_shodan_key()
        self.ipstack_api_key = ipstack_api_key or self._load_ipstack_key()
        self.numverify_api_key = numverify_api_key or self._load_numverify_key()
        self._shodan = None

    def _load_shodan_key(self) -> Optional[str]:
        """Load Shodan API key from reconspider config."""
        try:
            from core.config import shodan_api
            return shodan_api
        except ImportError:
            return None

    def _load_ipstack_key(self) -> Optional[str]:
        """Load IPStack API key from reconspider config."""
        try:
            from plugins.api import ipstack
            return ipstack()
        except ImportError:
            return None

    def _load_numverify_key(self) -> Optional[str]:
        """Load NumVerify API key from reconspider config."""
        try:
            from plugins.api import phoneapis
            return phoneapis()
        except ImportError:
            return None

    @property
    def shodan(self):
        """Lazy load Shodan API client."""
        if self._shodan is None and self.shodan_api_key:
            try:
                import shodan
                self._shodan = shodan.Shodan(self.shodan_api_key)
            except ImportError:
                pass
        return self._shodan

    def ip_lookup(self, ip: str) -> OSINTResult:
        """
        Lookup IP address information using IPStack.

        Returns geolocation, ISP, and other metadata.
        """
        if not self.ipstack_api_key:
            return OSINTResult(success=False, error="IPStack API key not configured")

        try:
            url = f"https://api.ipstack.com/{ip}?access_key={self.ipstack_api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                return OSINTResult(success=False, error=data["error"].get("info", "Unknown error"))

            return OSINTResult(
                success=True,
                data={
                    "ip": data.get("ip"),
                    "type": data.get("type"),
                    "continent": data.get("continent_name"),
                    "country": data.get("country_name"),
                    "country_code": data.get("country_code"),
                    "region": data.get("region_name"),
                    "city": data.get("city"),
                    "zip": data.get("zip"),
                    "latitude": data.get("latitude"),
                    "longitude": data.get("longitude"),
                }
            )
        except requests.RequestException as e:
            return OSINTResult(success=False, error=str(e))

    def shodan_lookup(self, ip: str) -> OSINTResult:
        """
        Lookup IP address information using Shodan.

        Returns open ports, services, organization info.
        """
        if not self.shodan:
            return OSINTResult(success=False, error="Shodan API not configured or not installed")

        try:
            import shodan
            host = self.shodan.host(ip)
            return OSINTResult(
                success=True,
                data={
                    "ip": host.get("ip_str"),
                    "organization": host.get("org"),
                    "isp": host.get("isp"),
                    "asn": host.get("asn"),
                    "country": host.get("country_name"),
                    "city": host.get("city"),
                    "ports": host.get("ports", []),
                    "hostnames": host.get("hostnames", []),
                    "vulns": host.get("vulns", []),
                    "last_update": host.get("last_update"),
                }
            )
        except shodan.APIError as e:
            return OSINTResult(success=False, error=f"Shodan API error: {e}")
        except Exception as e:
            return OSINTResult(success=False, error=str(e))

    def honeypot_check(self, ip: str) -> OSINTResult:
        """
        Check if an IP is likely a honeypot using Shodan.

        Returns honeypot probability score (0-100%).
        """
        if not self.shodan_api_key:
            return OSINTResult(success=False, error="Shodan API key not configured")

        try:
            url = f"https://api.shodan.io/labs/honeyscore/{ip}?key={self.shodan_api_key}"
            response = requests.get(url, timeout=10)

            if response.status_code == 404:
                return OSINTResult(success=False, error="IP not found in Shodan database")

            score = float(response.text)
            probability = score * 100

            return OSINTResult(
                success=True,
                data={
                    "ip": ip,
                    "honeypot_score": score,
                    "honeypot_probability": f"{probability:.1f}%",
                    "is_likely_honeypot": probability > 50,
                }
            )
        except (ValueError, requests.RequestException) as e:
            return OSINTResult(success=False, error=str(e))

    def phone_lookup(self, phone_number: str) -> OSINTResult:
        """
        Lookup phone number information using NumVerify.

        Returns carrier, location, line type.
        """
        if not self.numverify_api_key:
            return OSINTResult(success=False, error="NumVerify API key not configured")

        try:
            # Clean phone number
            clean_number = ''.join(c for c in phone_number if c.isdigit())

            url = f"https://apilayer.net/api/validate?access_key={self.numverify_api_key}&number={clean_number}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                return OSINTResult(success=False, error=data["error"].get("info", "Unknown error"))

            if not data.get("valid"):
                return OSINTResult(success=False, error="Invalid phone number")

            return OSINTResult(
                success=True,
                data={
                    "number": data.get("number"),
                    "local_format": data.get("local_format"),
                    "international_format": data.get("international_format"),
                    "country": data.get("country_name"),
                    "country_code": data.get("country_code"),
                    "location": data.get("location"),
                    "carrier": data.get("carrier"),
                    "line_type": data.get("line_type"),
                }
            )
        except requests.RequestException as e:
            return OSINTResult(success=False, error=str(e))

    def domain_lookup(self, domain: str) -> OSINTResult:
        """
        Lookup domain information using WHOIS and DNS.
        """
        try:
            import whois
            w = whois.whois(domain)

            if w is None or not w.domain_name:
                return OSINTResult(success=False, error=f"No WHOIS data found for {domain}")

            # Handle fields that can be lists or single values
            def get_first(val):
                if isinstance(val, list):
                    return val[0] if val else None
                return val

            return OSINTResult(
                success=True,
                data={
                    "domain": get_first(w.domain_name),
                    "registrar": w.registrar,
                    "creation_date": str(get_first(w.creation_date)) if w.creation_date else None,
                    "expiration_date": str(get_first(w.expiration_date)) if w.expiration_date else None,
                    "name_servers": w.name_servers if isinstance(w.name_servers, list) else [w.name_servers] if w.name_servers else [],
                    "status": w.status if isinstance(w.status, list) else [w.status] if w.status else [],
                    "org": w.org,
                    "country": w.country,
                }
            )
        except Exception as e:
            return OSINTResult(success=False, error=str(e))


# --- Pydantic Input Schemas ---

class IPLookupInput(BaseModel):
    ip: str = Field(..., description="IP address to lookup (e.g., '8.8.8.8')")

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        import re
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", v):
            raise ValueError("Invalid IP address format")
        return v


class DomainLookupInput(BaseModel):
    domain: str = Field(..., description="Domain to lookup (e.g., 'example.com')")

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v or "." not in v:
            raise ValueError("Invalid domain format")
        return v.lower().strip()


class PhoneLookupInput(BaseModel):
    phone_number: str = Field(..., description="Phone number with country code (e.g., '+1234567890')")


# --- LangChain Tools ---

def _format_result(result: OSINTResult, title: str) -> str:
    """Format OSINT result for output."""
    if not result.success:
        return f"Error: {result.error}"

    lines = [f"=== {title} ==="]
    for key, value in result.data.items():
        if value is not None:
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value) if value else "N/A"
            lines.append(f"  {key.replace('_', ' ').title()}: {value}")

    return "\n".join(lines)


@tool("osint_ip_lookup", args_schema=IPLookupInput)
def osint_ip_lookup(ip: str) -> str:
    """
    Lookup information about an IP address.

    Returns geolocation, country, city, ISP, and coordinates.
    Uses IPStack and Shodan APIs for comprehensive results.
    """
    client = OSINTClient()
    results = []

    # IPStack lookup
    ipstack_result = client.ip_lookup(ip)
    if ipstack_result.success:
        results.append(_format_result(ipstack_result, "IP GEOLOCATION"))

    # Shodan lookup
    shodan_result = client.shodan_lookup(ip)
    if shodan_result.success:
        results.append(_format_result(shodan_result, "SHODAN INTELLIGENCE"))

    if not results:
        return f"Error: Could not retrieve information for {ip}. Check API keys."

    return "\n\n".join(results)


@tool("osint_domain_lookup", args_schema=DomainLookupInput)
def osint_domain_lookup(domain: str) -> str:
    """
    Lookup WHOIS information for a domain.

    Returns registrar, creation date, name servers, and contact info.
    """
    client = OSINTClient()
    result = client.domain_lookup(domain)
    return _format_result(result, f"DOMAIN: {domain}")


@tool("osint_honeypot_check", args_schema=IPLookupInput)
def osint_honeypot_check(ip: str) -> str:
    """
    Check if an IP address is likely a honeypot.

    Returns probability score based on Shodan honeyscore API.
    Useful for identifying decoy systems during reconnaissance.
    """
    client = OSINTClient()
    result = client.honeypot_check(ip)
    return _format_result(result, f"HONEYPOT CHECK: {ip}")


@tool("osint_phone_lookup", args_schema=PhoneLookupInput)
def osint_phone_lookup(phone_number: str) -> str:
    """
    Lookup information about a phone number.

    Returns carrier, location, country, and line type.
    Phone number should include country code.
    """
    client = OSINTClient()
    result = client.phone_lookup(phone_number)
    return _format_result(result, f"PHONE: {phone_number}")
