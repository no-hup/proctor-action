#!/usr/bin/env python3
"""Emit concise GitHub Actions workflow annotations and headline banner from SARIF + Step Summary."""

import json
import os
import sys


def escape_cmd_value(value: str) -> str:
    """Escape special characters for GitHub workflow commands."""
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


def escape_prop(value: str) -> str:
    """Escape property values (file, title, etc.) in GitHub workflow commands."""
    return (
        escape_cmd_value(value)
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def main() -> int:
    if len(sys.argv) < 4:
        return 0

    sarif_path, summary_path, exit_code = sys.argv[1], sys.argv[2], int(sys.argv[3])
    guard_count = 0
    report_count = 0

    if sarif_path and os.path.exists(sarif_path):
        try:
            with open(sarif_path, encoding="utf-8") as f:
                sarif = json.load(f)
            results = (sarif.get("runs") or [{}])[0].get("results", [])
            for r in results:
                lvl = r.get("level", "warning")
                if lvl == "error":
                    guard_count += 1
                elif lvl == "warning":
                    report_count += 1

            # GitHub drops excess annotations after ~10 per step, so emit top 10 prioritized (errors first)
            ordered = sorted(
                results,
                key=lambda item: 0 if item.get("level") == "error" else 1,
            )
            for r in ordered[:10]:
                lvl = "error" if r.get("level") == "error" else "warning"
                rule = r.get("ruleId", "PROCTOR")
                msg = escape_cmd_value((r.get("message") or {}).get("text", "").strip())
                loc = (r.get("locations") or [{}])[0].get("physicalLocation", {})
                uri = (loc.get("artifactLocation") or {}).get("uri", "")
                line = (loc.get("region") or {}).get("startLine")
                props = []
                if uri:
                    props.append(f"file={escape_prop(uri)}")
                    if line:
                        props.append(f"line={line}")
                props.append(f"title={escape_prop(f'proctor {rule}')}")
                print(f"::{lvl} {','.join(props)}::{msg}")
        except Exception as exc:
            print(f"::warning title=proctor SARIF warning::{escape_cmd_value(str(exc))}")

    verify_parts = []
    if summary_path and os.path.exists(summary_path):
        try:
            with open(summary_path, encoding="utf-8") as f:
                txt = f.read()
            if "Dynamic Test Verification Receipt" in txt:
                catches = txt.count("| 🛡️ **Catches change** |")
                missing = txt.count("| ⚠️ **Missing on base** |")
                passes_both = txt.count("| ⚪ **Passes on both** |")
                broken = txt.count("| ❌ **Broken** |")
                inconclusive = txt.count("| ℹ️ **Inconclusive** |")
                if catches:
                    verify_parts.append(f"{catches} catches change")
                if passes_both:
                    verify_parts.append(f"{passes_both} passes on both")
                if missing:
                    verify_parts.append(f"{missing} missing on base")
                if broken:
                    verify_parts.append(f"{broken} broken")
                if inconclusive:
                    verify_parts.append(f"{inconclusive} inconclusive")
        except Exception:
            pass

    verify_note = f" | verify: {', '.join(verify_parts)}" if verify_parts else ""
    if guard_count == 0 and report_count == 0 and exit_code == 0:
        title = escape_prop(f"proctor: Clean test diff{verify_note}")
        print(f"::notice title={title}::No test tampering or assertion loosening detected.")
    else:
        title = escape_prop(f"proctor: {guard_count} guard, {report_count} review{verify_note}")
        print(f"::warning title={title}::Inspect Test-Change Receipt in Job Summary or SARIF.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
