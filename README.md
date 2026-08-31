# BigQuery Studio VDI Firewall Whitelist & Tenant Isolation Verification

This repository provides an automated testing harness and reference architecture for running **BigQuery Studio (Google Cloud Console)** in highly restrictive network environments (e.g. enterprise VDI workstations).

It demonstrates and validates:
1.  **VDI Egress Allowlist (17 Domains)**: A minimal list of FQDNs required for full BigQuery Studio functionality without allowing direct API egress.
2.  **Console Gateway Architecture**: Verification that the browser routes all BigQuery operations through `cloudconsole-pa.clients6.google.com` rather than contacting `bigquery.googleapis.com` directly.
3.  **GCP Organization Restrictions (`X-Goog-Allowed-Resources`)**: Automated header injection using `mitmproxy` to enforce tenant boundaries and block access to unauthorized GCP projects.
4.  **Google Workspace Domain Restrictions (`X-GoogApps-Allowed-Domains`)**: Automated header injection to restrict user account logins on `accounts.google.com` to authorized corporate domains.

---

## 1. Repository Structure

```
├── README.md                                         # Main project documentation & quickstart
├── requirements.txt                                  # Dependency declarations (mitmproxy, playwright)
├── .gitignore                                        # Configured ignore rules (docs/, test/, logs, profiles)
├── images/                                           # Architecture and sequence diagrams
│   ├── mermaid_sequence_diagram.jpg
│   └── mermaid_sequence_diagram.png
├── report/                                           # Comprehensive verification report
│   └── BigQuery_Studio_VDI_Firewall_Whitelist_and_API_Verification_Report.md
└── scripts/                                          # Core executable scripts (4 test runners + launchers)
    ├── launch_chromium.py                            # Playwright Chromium browser launcher
    ├── launch_chrome.sh                              # Direct system Google Chrome launcher
    │
    ├── proxy_org_restriction.py                      # Mitmproxy addon: Injects X-Goog-Allowed-Resources
    ├── start_org_proxy.sh                            # Runner: GCP Organization Restriction proxy
    │
    ├── proxy_domain_restriction.py                   # Mitmproxy addon: Injects X-GoogApps-Allowed-Domains
    └── start_domain_proxy.sh                         # Runner: Google Workspace Domain Restriction proxy
```

---

## 2. Minimal VDI FQDN Allowlist

To operate BigQuery Studio from a locked-down VDI client, firewalls only need to permit egress to these **17 domains**:

| Category | FQDN | Purpose |
| :--- | :--- | :--- |
| **Console Gateway & Shell** | `console.cloud.google.com` | Console UI Shell |
| | `cloud.google.com` | Marketing / Diagnostics / Logging |
| | `apis.google.com` | Google API Loader |
| | `clients6.google.com` | Drive & Auxiliary APIs |
| | `cloudconsole-pa.clients6.google.com` | **Console Gateway (BigQuery Actions)** |
| | `cloudresourcemanager.clients6.google.com`| Resource Management Gateway |
| | `cloudusersettings-pa.clients6.google.com` | User UI Settings Gateway |
| | `waa-pa.clients6.google.com` | Web Assistant Gateway |
| **MFA & Authentication** | `accounts.google.com` | Core Google Login |
| | `reauth.cloud.google.com` | **MFA Token Refresh (Required to avoid hangs)** |
| | `www.google.com` | General Auth Verification |
| **CDNs, Fonts, Assets** | `www.gstatic.com` | Google Static Assets |
| | `ssl.gstatic.com` | Google Static Security Assets |
| | `fonts.gstatic.com` | Google Font Assets |
| | `fonts.googleapis.com` | Google Fonts API |
| | `lh3.googleusercontent.com` | User Profile Icons |
| | `www.googletagmanager.com` | Tag Management |

---

## 3. Prerequisites & Setup

### Requirements
*   Linux / macOS / Windows (WSL2)
*   Python 3.10+
*   Google Cloud Organization & Project access

### Quickstart Installation
1.  Clone this repository:
    ```bash
    git clone git@github.com:Royston88/mitmweb-proxy-gcp-tests.git
    cd mitmweb-proxy-gcp-tests
    ```
2.  Set up the Python virtual environment:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
3.  Install Playwright browser binaries:
    ```bash
    playwright install chromium
    ```

---

## 4. How to Test & Verify

### Test Suite 1: GCP Organization Restrictions (`X-Goog-Allowed-Resources`)

This test verifies that injecting `X-Goog-Allowed-Resources` on `*.clients6.google.com` and `*.googleapis.com` restricts access strictly to projects in your authorized organization.

1.  **Start the Organization Proxy**:
    *   **Fake / Unauthorized Org (Expected: BLOCKED)**:
        ```bash
        ./scripts/start_org_proxy.sh fake_org
        ```
    *   **Real / Authorized Org (Expected: ALLOWED)**:
        ```bash
        ./scripts/start_org_proxy.sh real_org YOUR_ORGANIZATION_ID
        ```
    *   **Passthrough (Control Baseline)**:
        ```bash
        ./scripts/start_org_proxy.sh passthrough
        ```
2.  **Launch the Browser**:
    ```bash
    export GCP_PROJECT_ID="YOUR_GCP_PROJECT_ID"
    export DISPLAY=":0"   # Adjust if running inside VNC / Cloudtop CRD (e.g., :20)

    python3 scripts/launch_chromium.py
    ```
3.  **Expected Outcomes**:
    *   In **`fake_org`** mode: Executing queries or expanding projects returns an *"Access denied by organization restriction"* modal.
    *   In **`real_org`** mode: Query succeeds and displays results.

---

### Test Suite 2: Google Workspace Domain Restrictions (`X-GoogApps-Allowed-Domains`)

This test verifies that injecting `X-GoogApps-Allowed-Domains` on `accounts.google.com` restricts user sign-ins strictly to corporate Google Workspace accounts.

1.  **Start the Domain Restriction Proxy**:
    *   **Blocked / Unauthorized Domain (Expected: SIGN-IN BLOCKED)**:
        ```bash
        ./scripts/start_domain_proxy.sh blocked_domain
        ```
    *   **Allowed Corporate Domain (Expected: SIGN-IN PERMITTED)**:
        ```bash
        ./scripts/start_domain_proxy.sh allowed_domain yourcompany.com
        ```
    *   **Passthrough (Control Baseline)**:
        ```bash
        ./scripts/start_domain_proxy.sh passthrough
        ```
2.  **Launch the Browser (Targeting Login)**:
    ```bash
    export TARGET_URL="https://accounts.google.com"
    export DISPLAY=":0"

    python3 scripts/launch_chromium.py
    ```
3.  **Expected Outcomes**:
    *   In **`blocked_domain`** mode: Attempting to log into a personal `@gmail.com` or unauthorized corporate account displays the Google Identity block page: *"Access blocked: Your organization has restricted access to this service"*.
    *   In **`allowed_domain`** mode: Users with `@yourcompany.com` can sign in normally.

### Resetting Browser Profile & Switching Tests

Browser cookies and session credentials are saved persistently under `~/.config/playwright-chromium-profile`. When switching between test suites or executing a clean sign-in test without cached credentials, reset the default profile with:

```bash
rm -rf ~/.config/playwright-chromium-profile
```

To stop any running proxy or browser process:
* **Stop Proxy**: Press `Ctrl + C` in the proxy terminal or run `fuser -k 8080/tcp 8081/tcp`.
* **Stop Browser**: Press `Ctrl + C` in the browser launcher terminal or simply close the browser window.

---

### Mitmweb Dashboard
While any proxy is running, open the **Mitmweb Web UI** at `http://127.0.0.1:8081` to view live traffic interception and inspect injected headers in real-time.

---

## 5. License
MIT License.
