# Proctor Anticheat Rule Catalog

This document details the complete rule specifications and invariant checks enforced by `agent-proctor`.

---

## Summary of Detection Invariants

| Rule ID | Name | Default Tier | Exit Code (Default) | Exit Code (`--strict`) | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`PROCTOR-001`** | Test Case Deletion | **Guard** | `2` (BLOCK) | `2` (BLOCK) | Prevents deleting test functions or test files unless the tested production code was also deleted. |
| **`PROCTOR-002`** | Assertion Weakening | **Report** / Guard | `0` (Advisory) | `1` (BLOCK) | Catches relaxing assertions (e.g. `assert x == 5` to `assert x is not None` or `assert True`). |
| **`PROCTOR-003`** | SUT Shadow Mocking | **Guard** | `2` (BLOCK) | `2` (BLOCK) | Prevents mocking the function or class under test to fake test passes. |
| **`PROCTOR-004`** | Runner Config Tampering | **Guard** | `2` (BLOCK) | `2` (BLOCK) | Flags altering runner configs (`pytest.ini`, `setup.cfg`, `jest.config`) to ignore errors or drop coverage. |
| **`PROCTOR-005`** | CI Workflow Sabotage | **Guard** | `2` (BLOCK) | `2` (BLOCK) | Flags appending `\|\| true`, `; exit 0`, or `--continue-on-error` to CI test steps. |
| **`PROCTOR-006`** | Skip / Flakiness Quarantine | **Report** / Guard | `0` (Advisory) | `1` (BLOCK) | Flags injecting `@pytest.mark.skip` or `test.skip` when production code was modified in the same PR. |
| **`PROCTOR-007`** | Policy Degradation | **Guard** | `3` (FATAL) | `3` (FATAL) | Prevents PRs from tampering with `proctor.toml` or policy base commits. |

---

## Detailed Rule Specifications

### PROCTOR-001: Test Case Deletion
* **Attack Vector:** An agent fails to solve an edge case and simply deletes the failing test function or removes lines from a table-driven parametrization.
* **The Invariant:** A test case may only be removed if **all referenced production symbols** in that test function have been removed from the production codebase (an intentional feature retirement). If the production symbols still exist, the deletion is classified as test demolition.
* **Tier:** Guard (Exit 2).

---

### PROCTOR-002: Assertion Weakening Lattice
* **Attack Vector:** An agent mutates an exact assertion (`assert res.status == 200`) into a loose check (`assert res is not None` or `assert True`) to achieve a green test runner.
* **The Invariant:** Tree-sitter parses the assertion AST before and after the diff, evaluating transitions across the strength lattice:
  $$\text{Vacuous} < \text{Weak} < \text{Exact}$$
  Downgrading from Exact to Weak or Vacuous without removing the underlying production symbol is flagged.
* **Tier:** Report (Exit 0 default / Exit 1 under `--strict`). Guard if done without touching production code.

---

### PROCTOR-003: SUT Shadow Mocking
* **Attack Vector:** The agent is tasked with fixing `calculate_tax()`. Instead of fixing the algorithm, it injects `@patch("billing.calculate_tax", return_value=42.0)` inside the test body.
* **The Invariant:** Mocks are permitted for external architectural boundaries (HTTP calls, database connections, filesystem I/O). Mocks targeting symbols defined in the module under test that are directly asserted in the test body are blocked.
* **Tier:** Guard (Exit 2).

---

### PROCTOR-004: Runner Configuration Tampering
* **Attack Vector:** The agent edits `pytest.ini`, `pyproject.toml`, or `setup.cfg` to append flags like `--ignore-glob`, `--tb=no`, or disable strict failure thresholds.
* **The Invariant:** Modifying test runner discovery configs or suppression flags in the same PR that modifies code is blocked.
* **Tier:** Guard (Exit 2).

---

### PROCTOR-005: CI Workflow Sabotage
* **Attack Vector:** The agent edits `.github/workflows/*.yml` to change `run: pytest` to `run: pytest || true` or `run: pytest; exit 0`.
* **The Invariant:** Appending exit code overrides or ignore flags to test runner steps is blocked.
* **Tier:** Guard (Exit 2).

---

### PROCTOR-006: Skip Marker / Flakiness Quarantine
* **Attack Vector:** The agent marks failing tests with `@pytest.mark.skip`, `@pytest.mark.xfail`, or `it.skip()`.
* **The Invariant:** Quarantining flaky tests is a legitimate human maintenance activity *only when done in isolation*. If skip markers are added in a PR that also modifies production code, it is blocked as an evasive pass.
* **Tier:** Report (if isolated test-only quarantine) / Guard (if combined with production code).

---

### PROCTOR-007: Policy Degradation
* **Attack Vector:** An agent edits `proctor.toml` in the PR branch to disable rules or add wildcard waivers (`*`).
* **The Invariant:** `proctor` strictly evaluates policy from the **base commit (`base_ref`)** via git object trees. The PR's head commit cannot downgrade its own evaluation policy.
* **Tier:** Guard (Exit 3).
