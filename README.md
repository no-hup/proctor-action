# agent-proctor GitHub Action

[![Free for Open Source](https://img.shields.io/badge/License-Free%20for%20Open%20Source-blue.svg)](LICENSE)
[![Zero Network Egress](https://img.shields.io/badge/Network-Zero--Egress%20Airgapped-success.svg)](#security-privacy--zero-egress-guarantees)
[![GitHub Sigstore Attestation](https://img.shields.io/badge/Provenance-GitHub%20Sigstore%20Verified-blue.svg)](#cryptographic-build-provenance)
[![Latency](https://img.shields.io/badge/Latency-%3C50ms-green.svg)]()
[![Determinism](https://img.shields.io/badge/Engine-Zero--LLM%20Tree--sitter-orange.svg)]()

> **Stop autonomous AI coding agents from submitting pull requests that make CI green by silently deleting tests, weakening assertions, or sabotaging test runners.**

---

## The Problem in Open Source

As autonomous AI agents (Devin, Claude Code, Cursor, Copilot Workspace) proliferate, open source maintainers are increasingly flooded with "drive-by" pull requests that claim to resolve open issues.

When an AI agent cannot solve a subtle edge case, empirical research shows it frequently reward-hacks the test suite:
* **Assertion Weakening:** Replaces `assert result.status == 200` with `assert result is not None` or `assert True`.
* **Test Deletion:** Deletes failing test functions or drops rows from parametrized tables.
* **Shadow Mocking:** Injects mocks directly into the system under test to force tests to pass without fixing the bug.
* **CI Sabotage:** Appends `|| true` or `; exit 0` to GitHub Actions workflow steps.

Negative prompts in `AGENT.md` or PR instructions **do not stop this behavior** (METR research demonstrated a 30.4% reward-hacking rate even on frontier reasoning models).

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

## ⚡ Quick Start: 5-Line GitHub Action

Add `.github/workflows/proctor.yml` to your repository:

```yaml
name: Test Integrity Anticheat

on:
  pull_request:
    branches: [main, master]

permissions:
  contents: read
  pull-requests: read
  security-events: write

jobs:
  proctor:
    name: Proctor PR Anticheat
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run agent-proctor anticheat gate
        uses: no-hup/proctor-action@v1
        with:
          base-ref: ${{ github.event.pull_request.base.sha }}
          head-ref: ${{ github.event.pull_request.head.sha }}
          sarif-file: proctor-results.sarif

      - name: Upload SARIF to GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: proctor-results.sarif
```

---

## Autonomous Agent Mode (`strict: 'true'`)

For unattended, automated agent PRs (e.g. sweep bots, Devin, OpenHands), configure `strict: 'true'`:

```yaml
      - name: Run agent-proctor anticheat gate
        uses: no-hup/proctor-action@v1
        with:
          strict: 'true'  # Enforce exit 1 on Report findings for automated bots
```

Under `--strict`, any assertion modifications coincident with production code changes require an explicit author acknowledgment or maintainer waiver before merging.

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

`agent-proctor` is **Free forever for Public Open Source Repositories** under an OSI-approved license.

For enterprise private repositories or commercial licensing, contact: `license@no-hup.dev`.
