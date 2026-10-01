"""upstream.proxy must reach every httpx client that talks to Cline."""

from __future__ import annotations

import asyncio

import httpx

from cline_gateway.config import Config, UpstreamConfig, load_config
from cline_gateway.model_catalog import ModelCatalog
from cline_gateway.registry import Registry
from cline_gateway.tokens import TokenManager
from cline_gateway.upstream import UpstreamClient

SOCKS = "socks5h://127.0.0.1:1080"
HTTP = "http://127.0.0.1:10809"


def _proxy_url(client: httpx.AsyncClient) -> str:
    """The proxy a client mounts, or "" when it goes direct."""
    for transport in client._mounts.values():
        url = getattr(getattr(transport, "_pool", None), "_proxy_url", None)
        if url is not None:
            return f"{url.scheme.decode()}://{url.host.decode()}:{url.port}"
    return ""


def test_upstream_client_mounts_config_proxy():
    up = UpstreamClient(UpstreamConfig(proxy=SOCKS))
    assert _proxy_url(up._client) == SOCKS


def test_upstream_client_goes_direct_by_default(monkeypatch):
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.delenv(var, raising=False)
    up = UpstreamClient(UpstreamConfig())
    assert _proxy_url(up._client) == ""


def test_token_refresh_client_mounts_proxy():
    cfg = Config(upstream=UpstreamConfig(proxy=HTTP))
    mgr = TokenManager(cfg, pool=None)  # type: ignore[arg-type]
    assert _proxy_url(mgr._client) == HTTP
    asyncio.run(mgr._client.aclose())


def test_model_catalog_mounts_proxy():
    cat = ModelCatalog("https://api.cline.bot/api/v1", Registry(), proxy=SOCKS)
    assert _proxy_url(cat._client) == SOCKS


def test_config_yaml_and_env_override(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(f"upstream:\n  proxy: {SOCKS}\n", encoding="utf-8")
    assert load_config(cfg_file).upstream.proxy == SOCKS

    monkeypatch.setenv("CLINE_GATEWAY_UPSTREAM__PROXY", HTTP)
    assert load_config(cfg_file).upstream.proxy == HTTP
