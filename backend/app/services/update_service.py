"""Checagem de novas versões do ProntoPsi.

Consulta a última release publicada no repositório público
`prontopsi-releases` no GitHub e compara com a versão instalada. É best-effort:
sem internet ou sem releases, apenas informa que não há atualização.
"""
from __future__ import annotations

import json
import logging
import re
from urllib.request import Request, urlopen

from ..config import APP_VERSION, RELEASES_REPO

logger = logging.getLogger("anamnese")


def _parse_version(tag: str) -> tuple[int, ...]:
    """Converte 'v1.2.3' ou '1.2.3' em (1, 2, 3) para comparar."""
    nums = re.findall(r"\d+", tag or "")
    return tuple(int(n) for n in nums) or (0,)


def _is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def check_update(timeout: float = 6.0) -> dict:
    """Retorna a situação da atualização.

    { current, latest, update_available, url, notes }.
    Nunca levanta erro: em falha, update_available=False.
    """
    result = {
        "current": APP_VERSION,
        "latest": None,
        "update_available": False,
        "url": f"https://github.com/{RELEASES_REPO}/releases",
        "notes": "",
    }
    url = f"https://api.github.com/repos/{RELEASES_REPO}/releases/latest"
    req = Request(url, headers={"Accept": "application/vnd.github+json",
                                "User-Agent": "ProntoPsi"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # sem internet, sem release (404), etc.
        logger.info("Checagem de atualização indisponível: %s", exc)
        return result

    tag = data.get("tag_name") or data.get("name") or ""
    result["latest"] = tag
    result["notes"] = data.get("body") or ""
    if data.get("html_url"):
        result["url"] = data["html_url"]
    result["update_available"] = bool(tag) and _is_newer(tag, APP_VERSION)
    return result
