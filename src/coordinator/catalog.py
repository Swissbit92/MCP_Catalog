# src/coordinator/catalog.py
from __future__ import annotations
import os, yaml
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class LaunchSpec:
    cmd: str
    args: List[str]
    env: Dict[str, str]

@dataclass
class ServerSpec:
    name: str
    kind: str  # "stdio"
    launch: LaunchSpec

@dataclass
class Catalog:
    servers: Dict[str, ServerSpec]

def _expand_env(d: Dict[str, str]) -> Dict[str, str]:
    return {k: os.path.expandvars(str(v)) for k, v in (d or {}).items()}

def load_catalog(path: str) -> Catalog:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    servers = {}
    for name, spec in (raw.get("servers") or {}).items():
        kind = spec.get("kind", "stdio")
        launch = spec.get("launch") or {}
        env = _expand_env(launch.get("env") or {})
        servers[name] = ServerSpec(
            name=name,
            kind=kind,
            launch=LaunchSpec(
                cmd=launch.get("cmd", ""),
                args=list(launch.get("args") or []),
                env=env,
            ),
        )
    return Catalog(servers=servers)
