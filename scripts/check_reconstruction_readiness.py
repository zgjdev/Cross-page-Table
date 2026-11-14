"""只读核验证据并列出G0–G3缺口；人工关口由外部审查决定。"""

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

REQUIREMENTS = {
    "data_integrity": ("G0", False, "输入版本、来源与覆盖完整"),
    "contamination_disposition": ("G0", False, "已知污染均有版本化处置"),
    "coordinate_audit": ("G0", True, "20坐标样例无未解释问题，包括方向和边界"),
    "score_contract": ("G0", False, "网格往返与冻结评分契约通过"),
    "research_space": ("G1", True, "200表分层审计、强规则和保持文本的人工结构修复"),
    "model_smoke": ("G2", False, "8–16表接口过拟合、50步smoke及恢复梯度验证"),
    "mechanism_signal": ("G3", True, "不超过500表的预算匹配对照及跨页机制信号"),
}
SCOPES = {
    "data_preparation": ["data_integrity"],
    "diagnostic_inference": list(REQUIREMENTS)[:4],
    "full_training": list(REQUIREMENTS),
}


def safe(root, value):
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError("evidence path escapes project")
    return path


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(root, reference):
    path = safe(root, reference["path"])
    expected = reference.get("sha256", "")
    if not re.fullmatch("[a-f0-9]{64}", expected):
        return None, ["缺少有效SHA-256"]
    if not path.is_file() or sha(path) != expected:
        return None, ["证据缺失或SHA-256不符"]
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    reasons = []
    if payload.get("status") != "completed":
        reasons.append("状态不是completed")
    coverage = payload.get("coverage", {})
    fields = ["expected", "completed", "missing", "extra", "duplicate"]
    if any(type(coverage.get(k)) is not int or coverage[k] < 0 for k in fields):
        reasons.append("缺少完整非负整数coverage")
    elif (
        coverage["expected"] == 0
        or coverage["completed"] != coverage["expected"]
        or any(coverage[k] != 0 for k in fields[2:])
    ):
        reasons.append("覆盖为空或存在缺失/额外/重复")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        reasons.append("缺少artifacts引用清单")
    else:
        for artifact in artifacts:
            target = safe(root, artifact["path"])
            if not target.is_file() or sha(target) != artifact.get("sha256"):
                reasons.append("关联产物缺失或SHA-256不符")
    if sha(path) != expected:
        reasons.append("证据检查期间发生变化")
    return payload, reasons


def check(root, manifest, scope):
    root = Path(root).resolve()
    if scope not in SCOPES:
        raise ValueError("invalid scope")
    records = {}
    for reference in manifest["evidence"]:
        kind = reference["kind"]
        if kind not in REQUIREMENTS or kind in records:
            raise ValueError("unknown or repeated evidence kind")
        records[kind] = (reference, *verify(root, reference))
    gaps, checked = [], []
    for kind in SCOPES[scope]:
        gate, human, description = REQUIREMENTS[kind]
        reasons = []
        if kind not in records:
            reasons.append("缺少证据引用")
        else:
            reference, payload, errors = records[kind]
            reasons.extend(errors)
            if not errors:
                checked.append(
                    {"kind": kind, "path": reference["path"], "sha256": reference["sha256"]}
                )
                if kind != "data_integrity":
                    checks = (payload or {}).get("checks", {})
                    required = {
                        "contamination_disposition": [
                            "all_known_overlaps_disposed",
                            "split_frozen",
                        ],
                        "score_contract": [
                            "roundtrip_passed",
                            "contract_passed",
                            "protocol_frozen",
                        ],
                        "model_smoke": [
                            "overfit_passed",
                            "gradients_updated",
                            "resume_passed",
                            "cache_passed",
                            "coverage_passed",
                        ],
                    }.get(kind, [])
                    if any(checks.get(key) is not True for key in required):
                        reasons.append("缺少该关口全部具名检查")
                    if kind == "model_smoke":
                        metrics = payload.get("metrics", {})
                        if not (
                            8 <= metrics.get("overfit_tables", 0) <= 16
                            and metrics.get("steps", 0) >= 50
                            and metrics.get("legal_rate", 0) >= 0.99
                            and metrics.get("source_coverage", 0) == 1
                        ):
                            reasons.append("G2样本/步数/合法率/来源覆盖未达标")
        if human:
            reasons.append("需要外部研究审查；本工具不将自报completed或approved转换为人工关口通过")
        for reason in reasons:
            gaps.append(dict(gate=gate, kind=kind, requirement=description, reason=reason))
    return dict(
        scope=scope,
        ready=not gaps,
        checked=checked,
        gaps=gaps,
        authority="evidence_preflight_only_not_execution_permission",
        human_gates_automatically_approved=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--scope", choices=SCOPES, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    source = safe(root, args.manifest)
    if sha(source) != args.manifest_sha256:
        raise ValueError("manifest SHA-256 mismatch")
    result = check(root, json.loads(source.read_text(encoding="utf-8-sig")), args.scope)
    if sha(source) != args.manifest_sha256:
        raise ValueError("manifest changed")
    result.update(
        manifest=args.manifest,
        manifest_sha256=args.manifest_sha256,
        implementation_sha256=sha(Path(__file__)),
        argv=sys.argv,
        utc=datetime.now(UTC).isoformat(),
    )
    output = safe(root, args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"ready": result["ready"], "gaps": len(result["gaps"])}))


if __name__ == "__main__":
    main()
