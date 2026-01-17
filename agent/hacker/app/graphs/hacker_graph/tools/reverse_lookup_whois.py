from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.graphs.hacker_graph.tools.helper import _require_binary, _run_cmd


class WhoisInput(BaseModel):
    query: str = Field(..., description="Domain or IP (e.g. example.com or 192.168.1.10).")

@tool("reverse_lookup_whois", args_schema=WhoisInput)
def reverse_lookup_whois(query: str) -> str:
    """
    Perform a whois lookup for a domain or IP. (No private-target restriction needed.)
    """
    query = query.strip()
    if any(ch in query for ch in [";", "&", "|", "$", "`"]):
        raise ValueError("Invalid characters in query.")
    _require_binary("whois")
    return _run_cmd(["whois", query], timeout_s=60)
