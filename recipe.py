#!/usr/bin/env python3
"""Pin public source and render reviewed TP2 commands; never starts a service."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parent
LOCK = json.loads((ROOT / "lock.json").read_text())


def patch_bytes(name: str) -> bytes:
    spec = LOCK.get("patches", {}).get(name)
    if spec is None:
        return b""
    data = (ROOT / spec["path"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != spec["sha256"]:
        raise ValueError(f"patch checksum mismatch: {name}")
    return data


def source_status(name: str) -> dict:
    directory = ROOT / "upstream" / name
    expected = LOCK["sources"][name]["revision"]
    if not (directory / ".git").is_dir():
        return {"source": name, "expected": expected, "ready": False}
    actual = subprocess.check_output(
        ["git", "-C", str(directory), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(
        ["git", "-C", str(directory), "status", "--porcelain"], text=True).strip()
    expected_patch = patch_bytes(name)
    diff = subprocess.check_output(["git", "-C", str(directory), "diff", "--binary", "HEAD"])
    untracked = subprocess.check_output(
        ["git", "-C", str(directory), "ls-files", "--others", "--exclude-standard"])
    patched = bool(expected_patch) and diff == expected_patch and not untracked
    return {"source": name, "expected": expected, "actual": actual,
            "clean": not dirty, "patch_applied": patched,
            "ready": actual == expected and (patched if expected_patch else not dirty)}


def apply_source_patch(name: str) -> None:
    data = patch_bytes(name)
    if not data:
        raise ValueError(f"no reviewed patch for {name}")
    status = source_status(name)
    if status["ready"]:
        return
    if status.get("actual") != status["expected"] or not status.get("clean"):
        raise ValueError(f"preserving mismatched/dirty source: {name}")
    base = ["git", "-C", str(ROOT / "upstream" / name), "apply"]
    subprocess.run([*base, "--check", "-"], input=data, check=True)
    subprocess.run([*base, "--index", "-"], input=data, check=True)
    if not source_status(name)["ready"]:
        raise ValueError(f"patched source did not match reviewed diff: {name}")


def fetch(name: str) -> None:
    """Fetch source only. Existing mismatched or modified copies are preserved."""
    directory = ROOT / "upstream" / name
    source = LOCK["sources"][name]
    if directory.exists():
        status = source_status(name)
        if not status["ready"] and not (status.get("clean") and status.get("actual") == status["expected"]):
            raise ValueError(f"preserving mismatched/dirty source: {directory}")
        return
    directory.mkdir(parents=True)
    for args in (["init", str(directory)],
                 ["-C", str(directory), "remote", "add", "origin", source["url"]],
                 ["-C", str(directory), "fetch", "--depth", "1", "origin", source["revision"]],
                 ["-C", str(directory), "checkout", "--detach", "FETCH_HEAD"]):
        subprocess.run(["git", *args], check=True)
    status = source_status(name)
    if status.get("actual") != status["expected"] or not status["clean"]:
        raise ValueError("source revision did not match lock")


def validate_site(site: dict) -> None:
    example = json.loads((ROOT / "site.example.json").read_text())
    if not isinstance(site, dict):
        raise ValueError("site must be a JSON object")
    required = set(example)
    if set(site) != required:
        raise ValueError(f"site keys differ: {sorted(set(site) ^ required)}")
    for key, value in site.items():
        if type(value) is not type(example[key]):
            raise ValueError(f"wrong type for site value: {key}")
        if isinstance(value, str) and (not value or "REPLACE" in value or
                                      any(ord(c) < 32 for c in value)):
            raise ValueError(f"fill a valid site value: {key}")
    ip = ipaddress.IPv4Address(site["head_ip"])
    if ip.is_unspecified or ip.is_multicast or ip.is_loopback:
        raise ValueError("head_ip must be the head node's fabric IPv4 address")
    if ip in ipaddress.IPv4Network("192.0.2.0/24"):
        raise ValueError("replace the documentation-only example head_ip")
    for key in ("link_port", "api_port"):
        if type(site[key]) is not int or not 1024 <= site[key] <= 65535:
            raise ValueError(f"invalid {key}")
    if site["link_port"] == site["api_port"]:
        raise ValueError("link_port and api_port must differ")
    if type(site["gid_index"]) is not int or not 0 <= site["gid_index"] <= 255:
        raise ValueError("invalid gid_index")
    for key in ("model", "cache", "kit", "engram", "token_map", "key_file", "bin_dir"):
        if not isinstance(site[key], str) or not site[key].startswith("/"):
            raise ValueError(f"{key} must be an absolute path inside the container")
    for key in ("hca", "interface", "served_name"):
        if not re.fullmatch(r"[A-Za-z0-9_.:,/-]+", site[key]):
            raise ValueError(f"invalid {key}")


def commands(site: dict, profile: str) -> dict:
    validate_site(site)
    p = LOCK["profiles"][profile]
    common = {"TF_DS_REPLAY_FLOOR": "1", "NCCL_IB_HCA": site["hca"],
              "NCCL_IB_GID_INDEX": str(site["gid_index"]),
              "TF_RDMA_GID_INDEX": str(site["gid_index"]),
              "NCCL_SOCKET_IFNAME": site["interface"]}
    if p.get("gpu_candidates"):
        common["TF_DS_GPU_CANDIDATES"] = "1"
    worker = [site["bin_dir"] + "/tf-dsv41-lanes", site["model"], site["cache"],
              "1", "2", site["head_ip"], str(site["link_port"]), site["kit"],
              "--engram", site["engram"], "--token-map", site["token_map"],
              "--pool", str(p["pool_tokens"]), "--streams", str(p["streams"]),
              "--round-rows", str(p["round_rows"]), "--rdma", site["hca"],
              "--graphs", "1", "--side", "1", "--prefetch", "1", "--aio", "1"]
    head_env = dict(common, TF_TP_WORLD="2", TF_TP_MASTER=site["head_ip"],
                    TF_TP_PORT=str(site["link_port"]), TF_DS_RANK_CACHE=site["cache"],
                    TF_DS_KIT=site["kit"], TENSORFOLD_CUDA_KERNELS=site["kit"] + "/aot",
                    TF_DS_ENGRAM=site["engram"], TF_DS_TOKEN_MAP=site["token_map"],
                    TF_RDMA_DEVICES=site["hca"], TF_DS_GRAPHS="1", TF_DS_HC_SIDE="1",
                    TF_DS_L2_PREFETCH="1", TF_DS_ENGRAM_AIO="1",
                    TF_DS_STREAMS=str(p["streams"]), TF_DS_ROUND_ROWS=str(p["round_rows"]))
    head = [site["bin_dir"] + "/tensorfold-native", "serve", site["model"],
            "--host", "127.0.0.1", "--port", str(site["api_port"]),
            "--name", site["served_name"], "--api-key-file", site["key_file"],
            "--context", str(p["pool_tokens"]), "--parallel", str(p["streams"]),
            "--thinking", "--max-tokens", "32768", "--temperature", "1.0",
            "--top-p", "0.95", "--top-k", "20", "--backend", "cuda"]
    return {"profile": profile, "qualified_here": False, "start_order": ["worker", "head"],
            "shared_pool_tokens": p["pool_tokens"],
            "worker": {"env": common, "argv": worker},
            "head": {"env": head_env, "argv": head}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    f = sub.add_parser("fetch")
    f.add_argument("source", choices=LOCK["sources"])
    p = sub.add_parser("patch")
    p.add_argument("source", choices=LOCK.get("patches", {}))
    r = sub.add_parser("render")
    r.add_argument("--site", type=Path, required=True)
    r.add_argument("--profile", choices=LOCK["profiles"], default="accepted-c8")
    r.add_argument("--shell", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "fetch":
            fetch(args.source)
            print(json.dumps(source_status(args.source), indent=2))
        elif args.action == "patch":
            apply_source_patch(args.source)
            print(json.dumps(source_status(args.source), indent=2))
        elif args.action == "status":
            print(json.dumps({"sources": [source_status(n) for n in LOCK["sources"]],
                              "toolchain": LOCK["toolchain"], "gpu_qualified": False}, indent=2))
        else:
            if not source_status("native")["ready"]:
                raise ValueError("native source must match the pinned base and reviewed patch before rendering")
            result = commands(json.loads(args.site.read_text()), args.profile)
            if args.shell:
                for rank in result["start_order"]:
                    command = result[rank]
                    print(f"# {rank}: run inside its prepared GB10 container")
                    print(shlex.join(["env", *[f"{k}={v}" for k, v in command["env"].items()],
                                      *command["argv"]]))
            else:
                print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"recipe: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
