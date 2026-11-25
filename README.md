# agent-proctor GitHub Action

[![Free for Open Source](https://img.shields.io/badge/License-Free%20for%20Open%20Source-blue.svg)](LICENSE)
[![Zero Network Egress](https://img.shields.io/badge/Network-Zero--Egress%20Airgapped-success.svg)](#security-privacy--zero-egress-guarantees)
[![GitHub Sigstore Attestation](https://img.shields.io/badge/Provenance-GitHub%20Sigstore%20Verified-blue.svg)](#cryptographic-build-provenance)
[![Latency](https://img.shields.io/badge/Latency-%3C200ms-green.svg)]()
[![Determinism](https://img.shields.io/badge/Engine-Zero--LLM%20Tree--sitter-orange.svg)]()

> **Prove your new tests fail on `base` and pass on `head` — and confirm existing test contracts stay intact.**

Every PR reviewer wants one clear answer before hitting merge: *"Do the new tests actually catch the bug, and did our existing tests keep their guarantees?"* `agent-proctor` runs fast static AST checks by default (`<200ms`), and can optionally execute added/modified tests against the base commit (`verify: 'true'`, experimental) to attach executable proof directly to `$GITHUB_STEP_SUMMARY`.

---

## 🔒 Security, Privacy & Zero-Egress Guarantees

We recognize that open-source maintainers must be vigilant about supply-chain integrity. `agent-proctor` is engineered with mathematically verifiable privacy guarantees:

1. **Zero-Egress Airgapped Architecture:**
   * The `proctor` binary is compiled with **zero networking libraries** (no `reqwest`, `hyper`, `curl`, sockets, or HTTP capabilities).
   * It **cannot** make outbound connections, phone home, send telemetry, or exfiltrate environment variables.
   * You can verify symbol isolation locally: `nm proctor | grep -i "socket\|connect\|http"` (returns 0 symbols).
2. **Least-Privilege Token Permissions:**
   * Proctor runs under strict read-only permissions (`contents: read`, `pull-requests: read`).
   * It **never** asks for and should never be granted `contents: write`, `id-token: write`, or access to repository secrets.
3. **Local SARIF Output (No Third-Party Servers):**
   * Findings are written locally to a standard file (`proctor-results.sarif`).
   * Rendering is performed by GitHub's official, open-source `github/codeql-action/upload-sarif@v3` action directly inside your repository's native **Security / Code Scanning** tab.

### Cryptographic Build Provenance

Every official `proctor` release binary is cryptographically signed and attested directly by GitHub's build infrastructure using **Sigstore / GitHub Artifact Attestations**. You can cryptographically verify that the binary was built cleanly on GitHub's official runners:

```bash
gh attestation verify proctor-linux-x86_64.tar.gz --owner no-hup
```

---

## ⚡ Quick Start: Add to Any PR Workflow

By default, `agent-proctor` runs static diff checks quietly in **Observe Mode (`enforce: false`)** — posting a concise summary receipt to `$GITHUB_STEP_SUMMARY` without failing CI. Set `verify: 'true'` *(experimental)* after your dependency install step to prove new tests reproduce the bug on `base`:

```yaml
name: Test Proof & Integrity

on:
  pull_request:
    branches: [main, master]

permissions:
  contents: read
  pull-requests: read
  security-events: write

jobs:
  proctor:
    name: Proctor Test Summary
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      # Optional: install dependencies first if enabling verify: 'true'
      - name: Run agent-proctor
        uses: no-hup/proctor-action@v1
        with:
          base-ref: ${{ github.event.pull_request.base.sha }}
          head-ref: ${{ github.event.pull_request.head.sha }}
          sarif-file: proctor-results.sarif
          verify: 'false'   # Set 'true' (after npm ci / pip install) to test new tests against base
          enforce: 'false'  # Default Observe Mode: reports summary, exits 0

      - name: Upload SARIF to GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: proctor-results.sarif
```

To enable hard blocking once you're satisfied with the baseline, set `enforce: true`.

---

## 🔒 Hermetic CI Alternative (Direct Checksum Pinning)

For teams requiring strict airgapped and pinned builds (zero external action wrappers), you can invoke the standalone binary directly with cryptographic SHA-256 verification:

```yaml
      - name: Run agent-proctor directly (Hermetic Pinning)
        shell: bash
        run: |
          mkdir -p /tmp/proctor-bin
          curl -sLf https://github.com/no-hup/proctor-action/releases/download/v0.2.0/proctor-linux-x86_64.tar.gz -o /tmp/proctor.tar.gz
          echo "e2c9dd27f93df030030216afb22889085b1e7de0e355e39fb66f576b8bf8c67a  /tmp/proctor.tar.gz" | sha256sum --check
          tar -xzf /tmp/proctor.tar.gz -C /tmp/proctor-bin
          chmod +x /tmp/proctor-bin/proctor
          /tmp/proctor-bin/proctor scan --base ${{ github.event.pull_request.base.sha }} --head ${{ github.event.pull_request.head.sha }} --sarif proctor-results.sarif
```

---

## 🧪 Dynamic Red/Green Verification (`verify: 'true'` — Experimental)

> **Experimental:** Off by default (`verify: 'false'`). Enable only on trusted `pull_request` workflows **after** installing dependencies (`npm ci` / `pip install`). Refused automatically under `pull_request_target`.

When enabled, `agent-proctor` verifies added and modified tests by running each test twice on `head`, temporarily swapping modified production files back to `base`, running twice on `base` (using pytest `--junitxml` or Jest/Vitest `--json`), and restoring the checkout:

- **Catches change (`Discriminating` in JSON)**: Passed 2x on `head` and failed 2x on `base` with an assertion failure.
- **Passes on both (`DoesNotDiscriminate` in JSON)**: Passed on both `head` and `base` (normal for refactor/coverage tests; review if testing a bugfix).
- **Missing on base (`MissingOnBase` in JSON)**: Failed on `base` due to an import or missing-symbol error.
- **Broken (`Broken` in JSON)**: Failed on `head`.
- **Inconclusive (`Inconclusive` in JSON)**: Timed out, flaky, dependency manifest changed, or setup/runner error (never alters exit code).

---

## Strict Mode (`strict: 'true'`)

For automated unattended PRs, configure `strict: 'true'`:

```yaml
      - name: Run agent-proctor
        uses: no-hup/proctor-action@v1
        with:
          strict: 'true'  # Enforce exit 1 on Report findings
```

Under `--strict`, assertion modifications coincident with production code changes require an explicit author acknowledgement or maintainer waiver before merging.

---

## Detection Rules & Specifications

For the complete specification of all detection invariants (`PROCTOR-001` through `PROCTOR-007`), see our [Rules Catalog](RULES_CATALOG.md).

---

## Acknowledging Legitimate Spec Changes

When a PR legitimately changes a feature's specification, authors can acknowledge findings directly in a PR comment:

```text
proctor: ack PROCTOR-002
```

For hard `Guard` findings, only repository collaborators with **write permissions** can grant a maintainer waiver:

```text
proctor: waive PROCTOR-001 reason="Breaking API refactor deprecating old endpoint"
```

Author comments can **never** waive Guard findings.

---

## License & Pricing

`agent-proctor` is **Free forever for Public Open Source Repositories** under the Apache-2.0 License.

For enterprise private repositories or commercial licensing, contact: `license@no-hup.dev`.
