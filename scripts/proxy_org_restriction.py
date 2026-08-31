"""
Google Cloud Organization Restriction Header Injector (X-Goog-Allowed-Resources).

Enforces tenant boundaries by injecting X-Goog-Allowed-Resources on all requests
to Google Cloud API gateways and console endpoints (*.clients6.google.com, *.googleapis.com).

Supported Modes (set via ORG_RESTRICTION_MODE env var):
  - 'fake_org'    : Injects Fake Org ID 000000000000 (Default -> Blocked)
  - 'real_org'    : Injects Authorized Org ID from ALLOWED_ORG_ID env var (Allowed)
  - 'foreign_org' : Injects Foreign Org ID 111122223333 (Blocked)
  - 'empty_org'   : Injects empty resources [] (Blocked)
  - 'passthrough' : Injects nothing (Baseline control)
"""

import os
import json
import base64
from datetime import datetime
from mitmproxy import http, ctx

def build_org_payload(org_id: str) -> str:
    """Helper to build Base64 JSON payload for X-Goog-Allowed-Resources header."""
    data = {"resources": [f"organizations/{org_id}"], "options": "strict"}
    return base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")

# Configure target authorized org from environment variable
TARGET_REAL_ORG = os.environ.get("ALLOWED_ORG_ID", "YOUR_ORGANIZATION_ID")

PAYLOADS = {
    "real_org": {
        "value": build_org_payload(TARGET_REAL_ORG),
        "desc": f"Real Org: {TARGET_REAL_ORG} (Expected: ALLOWED 200)"
    },
    "fake_org": {
        "value": "eyJyZXNvdXJjZXMiOlsib3JnYW5pemF0aW9ucy8wMDAwMDAwMDAwMDAiXSwib3B0aW9ucyI6InN0cmljdCJ9",
        "desc": "Fake Org: 000000000000 (Expected: BLOCKED 400/403)"
    },
    "foreign_org": {
        "value": "eyJyZXNvdXJjZXMiOlsib3JnYW5pemF0aW9ucy8xMTExMjIyMjMzMzMiXSwib3B0aW9ucyI6InN0cmljdCJ9",
        "desc": "Foreign Org: 111122223333 (Expected: BLOCKED 400/403)"
    },
    "empty_org": {
        "value": "eyJyZXNvdXJjZXMiOltdLCJvcHRpb25zIjoic3RyaWN0In0=",
        "desc": "Empty Org Array: [] (Expected: BLOCKED 400)"
    },
    "passthrough": {
        "value": None,
        "desc": "Passthrough (No Headers - Control Baseline)"
    }
}

AUDIT_LOG_FILE = os.environ.get("AUDIT_LOG_FILE", os.path.join(os.getcwd(), "proxy_traffic_audit.jsonl"))

class OrgRestrictionInjector:
    def __init__(self):
        self.mode = os.environ.get("ORG_RESTRICTION_MODE", "fake_org").lower()
        if self.mode not in PAYLOADS:
            ctx.log.warn(f"Unknown mode '{self.mode}', defaulting to 'fake_org'")
            self.mode = "fake_org"
        
        config = PAYLOADS[self.mode]
        ctx.log.info("=" * 60)
        ctx.log.info(f"[*] OrgRestrictionInjector Active | Mode: [{self.mode.upper()}]")
        ctx.log.info(f"[*] Description: {config['desc']}")
        if config["value"]:
            ctx.log.info(f"[*] Injecting: X-Goog-Allowed-Resources: {config['value']}")
        ctx.log.info(f"[*] Audit Log: {AUDIT_LOG_FILE}")
        ctx.log.info("=" * 60)

    def request(self, flow: http.HTTPFlow):
        host = flow.request.pretty_host
        # Match Google Cloud endpoints (clients6, googleapis)
        if "clients6.google.com" in host or "googleapis.com" in host:
            config = PAYLOADS[self.mode]
            if config["value"]:
                flow.request.headers["X-Goog-Allowed-Resources"] = config["value"]
                
                # Tag flow for logging
                flow.metadata["injected_header"] = "X-Goog-Allowed-Resources"
                flow.metadata["injected_value"] = config["value"]
                flow.metadata["mode"] = self.mode
                
                ctx.log.info(f"\033[94m[INJECT-ORG]\033[0m {flow.request.method} {flow.request.url[:80]}... | Added X-Goog-Allowed-Resources")

    def response(self, flow: http.HTTPFlow):
        host = flow.request.pretty_host
        if "clients6.google.com" in host or "googleapis.com" in host:
            status_code = flow.response.status_code
            status_color = "\033[92m" if status_code == 200 else "\033[91m"
            ctx.log.info(
                f"{status_color}[RESPONSE {status_code}]\033[0m {flow.request.method} {flow.request.url[:70]} "
                f"| Mode: {self.mode} | Header: {flow.metadata.get('injected_header', 'None')}"
            )
            
            # Log to structured JSONL file
            record = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "test_type": "org_restriction",
                "mode": self.mode,
                "url": flow.request.url,
                "host": host,
                "path": flow.request.path,
                "method": flow.request.method,
                "injected_header": flow.metadata.get("injected_header"),
                "injected_value": flow.metadata.get("injected_value"),
                "status_code": status_code,
                "response_size": len(flow.response.content) if flow.response.content else 0,
                "response_snippet": flow.response.text[:300] if flow.response.text else ""
            }
            
            try:
                with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
            except Exception as e:
                ctx.log.error(f"Error writing to audit log: {e}")

addons = [OrgRestrictionInjector()]
