import shutil
from typing import List

from langchain_core.tools import tool
from pydantic import BaseModel, Field, field_validator

from app.graphs.hacker_graph.tools.helper import _run_cmd, _looks_like_domain


class DNSReconInput(BaseModel):
    domain: str = Field(..., description="Domain name that resolves to private IPs (tool restricted).")
    record_types: List[str] = Field(
        default_factory=lambda: ["A", "AAAA", "MX", "NS", "TXT"],
        description="DNS record types to query in safe fallback mode.",
    )

    @field_validator("record_types")
    @classmethod
    def _validate_types(cls, v: List[str]) -> List[str]:
        allowed = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "SRV"}
        for t in v:
            if t.upper() not in allowed:
                raise ValueError(f"Unsupported record type: {t}")
        return [t.upper() for t in v]


@tool("domain_dnsrecon", args_schema=DNSReconInput)
def domain_dnsrecon(domain: str, record_types: List[str] = None) -> str:
    """
    DNS reconnaissance:
    - If `dnsrecon` exists, runs a conservative lookup.
    - Otherwise falls back to querying common record types via dnspython.
    Restricted: domain must resolve to private IPs.
    """
    domain = domain.strip().rstrip(".")
    if not _looks_like_domain(domain):
        raise ValueError("domain must look like a domain name (e.g. internal.example.local).")

    if shutil.which("dnsrecon") is not None:
        # dnsrecon modes can be very enumerative; keep it conservative.
        # -d domain, -t std = standard enumeration
        return _run_cmd(["dnsrecon", "-d", domain, "-t", "std"], timeout_s=120)

    # Fallback: safe record queries
    try:
        import dns.resolver  # type: ignore
    except Exception:
        raise FileNotFoundError("Neither 'dnsrecon' nor 'dnspython' is available. Install one of them.")

    if record_types is None:
        record_types = ["A", "AAAA", "MX", "NS", "TXT"]

    lines = [f"DNS records for {domain} (fallback mode):"]
    resolver = dns.resolver.Resolver()

    for rtype in record_types:
        try:
            ans = resolver.resolve(domain, rtype)
            vals = [a.to_text() for a in ans]
            lines.append(f"\n{rtype}:")
            lines.extend(f"- {v}" for v in vals)
        except Exception as e:
            lines.append(f"\n{rtype}: (no answer) {e}")

    return "\n".join(lines)