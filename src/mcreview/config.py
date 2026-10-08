"""Configuration, credentials and config hashing.

All replicable configuration lives in config/*.yaml. Credentials live outside the
repository (see settings.credentials.env_file) and are never part of the config hash.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_FILES = ("settings.yaml", "validation.yaml", "queries.yaml", "analysis.yaml", "codebook.yaml", "exclusions.yaml")
CREDENTIAL_KEYS = ("COOKIES_STRING", "BRAVE_API_KEY", "TYPESAFE_API_KEY", "ANTHROPIC_API_KEY")


def load_yaml(name: str) -> Any:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


class Settings:
    def __init__(self) -> None:
        self.raw: dict = load_yaml("settings.yaml")
        self.validation: dict = load_yaml("validation.yaml")
        self.queries: dict = load_yaml("queries.yaml")
        self.analysis: dict = load_yaml("analysis.yaml")
        self.exclusions: dict = load_yaml("exclusions.yaml") or {}

    def __getitem__(self, key: str) -> Any:
        return self.raw[key]

    def get(self, *keys: str, default: Any = None) -> Any:
        cur: Any = self.raw
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    def path(self, key: str) -> Path:
        p = Path(self.raw["paths"][key])
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def cutoff_date(self) -> str:
        return str(self.raw["cutoff_date"])

    def config_hash(self) -> str:
        h = hashlib.sha256()
        for name in CONFIG_FILES:
            h.update(name.encode())
            h.update((CONFIG_DIR / name).read_bytes())
        return h.hexdigest()

    def credentials(self) -> dict[str, str | None]:
        """CREDENTIAL_KEYS from the env file, overridden by real env vars.

        The file is parsed with python-dotenv, never sourced by a shell: cookie strings
        contain semicolons and spaces.
        """
        env_file = Path(os.path.expanduser(self.get("credentials", "env_file", default=""))) if self.get(
            "credentials", "env_file"
        ) else None
        vals: dict[str, str | None] = {}
        if env_file and env_file.is_file():
            vals.update(dotenv_values(env_file))
        out: dict[str, str | None] = {}
        for key in CREDENTIAL_KEYS:
            v = os.environ.get(key) or vals.get(key)
            out[key] = v.strip() if v else None
        # Guard against the template placeholder being left in place.
        if out["COOKIES_STRING"] and out["COOKIES_STRING"].startswith("paste-the-entire"):
            out["COOKIES_STRING"] = None
        return out

    def all_terms(self) -> list[tuple[str, str]]:
        """[(facet, term), ...] in file order."""
        return [(facet, term) for facet, terms in self.queries["facets"].items() for term in terms]
