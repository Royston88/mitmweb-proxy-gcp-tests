"""
Google Workspace Domain Restriction Header Injector (X-GoogApps-Allowed-Domains).

Restricts Google Account sign-ins to specified Google Workspace domains by injecting
X-GoogApps-Allowed-Domains on requests to Google Identity (accounts.google.com).

Supported Modes (set via DOMAIN_RESTRICTION_MODE env var):
  - 'blocked_domain': Injects 'unauthorized-corp-999.com' (Default -> Blocks personal/other logins)
  - 'allowed_domain': Injects Authorized Domain from ALLOWED_DOMAIN env var (Permits login)
  - 'passthrough'   : Injects nothing (Baseline control -> Allows any account)
"""

import os
import json
from datetime import datetime
from mitmproxy import http, ctx

TARGET_ALLOWED_DOMAIN = os.environ.get("ALLOWED_DOMAIN", "yourcompany.com")

PAYLOADS = {
    "allowed_domain": {
        "value": TARGET_ALLOWED_DOMAIN,
        "desc": f"Allowed Domain: {TARGET_ALLOWED_DOMAIN} (Expected: LOGIN PERMITTED for @{TARGET_ALLOWED_DOMAIN})"
    },
    "blocked_domain": {
        "value": "unauthorized-corp-999.com",
        "desc": "Blocked Domain: unauthorized-corp-999.com (Expected: LOGIN BLOCKED for personal/other domains)"
    },
    "passthrough": {
        "value": None,
        "desc": "Passthrough (No Headers - Control Baseline)"
    }
}

AUDIT_LOG_FILE = os.environ.get("AUDIT_LOG_FILE", os.path.join(os.getcwd(), "proxy_traffic_audit.jsonl"))

class DomainRestrictionInjector:
    def __init__(self):
        self.mode = os.environ.get("DOMAIN_RESTRICTION_MODE", "blocked_domain").lower()
        if self.mode not in PAYLOADS:
            ctx.log.warn(f"Unknown mode '{self.mode}', defaulting to 'blocked_domain'")
            self.mode = "blocked_domain"
        
        config = PAYLOADS[self.mode]
        ctx.log.info("=" * 60)
        ctx.log.info(f"[*] DomainRestrictionInjector Active | Mode: [{self.mode.upper()}]")
        ctx.log.info(f"[*] Description: {config['desc']}")
        if config["value"]:
            ctx.log.info(f"[*] Injecting: X-GoogApps-Allowed-Domains: {config['value']}")
        ctx.log.info(f"[*] Audit Log: {AUDIT_LOG_FILE}")
        ctx.log.info("=" * 60)

    def request(self, flow: http.HTTPFlow):
        host = flow.request.pretty_host
        # Match Google Accounts / Identity endpoints
        if "accounts.google.com" in host or "google.com" in host:
            config = PAYLOADS[self.mode]
            if config["value"]:
                flow.request.headers["X-GoogApps-Allowed-Domains"] = config["value"]
                
                # Tag flow for logging
                flow.metadata["injected_header"] = "X-GoogApps-Allowed-Domains"
                flow.metadata["injected_value"] = config["value"]
                flow.metadata["mode"] = self.mode
                
                ctx.log.info(f"\033[94m[INJECT-DOMAIN]\033[0m {flow.request.method} {flow.request.url[:80]}... | Added X-GoogApps-Allowed-Domains")

    def response(self, flow: http.HTTPFlow):
        host = flow.request.pretty_host
        if "accounts.google.com" in host:
            status_code = flow.response.status_code
            status_color = "\033[92m" if status_code == 200 else "\033[91m"
            ctx.log.info(
                f"{status_color}[RESPONSE {status_code}]\033[0m {flow.request.method} {flow.request.url[:70]} "
                f"| Mode: {self.mode} | Header: {flow.metadata.get('injected_header', 'None')}"
            )
            
            # Log to structured JSONL file
            record = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "test_type": "domain_restriction",
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

addons = [DomainRestrictionInjector()]
