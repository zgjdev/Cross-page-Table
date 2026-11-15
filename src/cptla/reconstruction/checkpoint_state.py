"""项目自产、显式受信任的模型/optimizer/RNG续训快照；禁止任意pickle加载。"""

import hashlib
import json
import random
from datetime import UTC, datetime
from pathlib import Path

FORMAT = "cptla-self-produced-training-state-v1"


def _path(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("checkpoint path escapes project or equals root")
    return path


def _hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _config_hash(config):
    return hashlib.sha256(
        json.dumps(
            config, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def save_state(project_root, name, model, optimizer, *, step, cursor, config):
    import torch

    if type(step) is not int or type(cursor) is not int or min(step, cursor) < 0:
        raise ValueError("invalid step/cursor")
    config_hash = _config_hash(config)
    directory = _path(project_root, name)
    directory.mkdir(parents=True, exist_ok=False)
    try:
        state = dict(
            format=FORMAT,
            model=model.state_dict(),
            optimizer=optimizer.state_dict(),
            torch_cpu_rng=torch.get_rng_state(),
            torch_cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
            python_rng=random.getstate(),
            step=step,
            cursor=cursor,
            config_hash=config_hash,
        )
        path = directory / "state.pt"
        with path.open("xb") as stream:
            torch.save(state, stream)
        manifest = dict(
            format=FORMAT,
            status="completed",
            state_file="state.pt",
            sha256=_hash(path),
            config_hash=config_hash,
            step=step,
            cursor=cursor,
            torch_version=str(torch.__version__),
            cuda_devices=len(state["torch_cuda_rng"]),
            utc=datetime.now(UTC).isoformat(),
        )
        with (directory / "manifest.json").open("x", encoding="utf-8") as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
    except (Exception, KeyboardInterrupt) as error:
        with (directory / "failure.json").open("x", encoding="utf-8") as stream:
            json.dump(dict(status="failed", exception_type=type(error).__name__), stream)
        raise
    return directory


def load_state(project_root, name, model, optimizer, *, config, trusted=False):
    """调用者须确认目录为本项目自产；SHA防意外变更，不认证恶意来源。"""
    import torch

    if trusted is not True:
        raise ValueError("explicit trusted self-produced checkpoint required")
    directory = _path(project_root, name)
    manifest_path = _path(directory, "manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_hash = _hash(manifest_path)
    if (
        manifest.get("format") != FORMAT
        or manifest.get("status") != "completed"
        or manifest.get("state_file") != "state.pt"
    ):
        raise ValueError("invalid checkpoint manifest")
    if manifest.get("config_hash") != _config_hash(config):
        raise ValueError("config mismatch")
    path = _path(directory, "state.pt")
    if _hash(path) != manifest.get("sha256"):
        raise ValueError("state SHA mismatch")
    state = torch.load(path, map_location="cpu", weights_only=True)
    if _hash(path) != manifest["sha256"] or _hash(manifest_path) != manifest_hash:
        raise ValueError("checkpoint SHA changed during read")
    if any(
        state.get(key) != manifest.get(key) for key in ("format", "config_hash", "step", "cursor")
    ):
        raise ValueError("checkpoint state/manifest mismatch")
    cuda_rng = state["torch_cuda_rng"]
    devices = torch.cuda.device_count() if torch.cuda.is_available() else 0
    if len(cuda_rng) != manifest["cuda_devices"] or len(cuda_rng) != devices:
        raise ValueError("CUDA RNG topology mismatch")
    # Validate RNG data in independent generators before changing live RNG state.
    probe = random.Random()
    probe.setstate(state["python_rng"])
    torch.Generator(device="cpu").set_state(state["torch_cpu_rng"])
    model.load_state_dict(state["model"], strict=True)
    optimizer.load_state_dict(state["optimizer"])
    random.setstate(state["python_rng"])
    torch.set_rng_state(state["torch_cpu_rng"])
    if cuda_rng:
        torch.cuda.set_rng_state_all(cuda_rng)
    return dict(step=state["step"], cursor=state["cursor"])
