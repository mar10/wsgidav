# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Check that the DAV Explorer only loads CDN files that are pinned with SRI hashes.

These checks are offline. Run `scripts/update_dav_explorer_cdn.py --check` to
verify the hashes against the CDN.
"""

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HTDOCS = ROOT / "wsgidav" / "mw" / "dav_explorer" / "htdocs"
SCRIPT = ROOT / "scripts" / "update_dav_explorer_cdn.py"

CDN = "https://cdn.jsdelivr.net/npm/"
RE_PINNED_URL = re.compile(
    r"^https://cdn\.jsdelivr\.net/npm/(?:@[\w.-]+/)?[\w.-]+@\d+\.\d+\.\d+/[\w./-]+\.(?:js|mjs|css)$"
)
RE_SRI = re.compile(r"^sha384-[A-Za-z0-9+/]{64}$")


@pytest.fixture(scope="module")
def cdn_tool():
    spec = importlib.util.spec_from_file_location("update_dav_explorer_cdn", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def app_html():
    return (HTDOCS / "app.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def importmap(cdn_tool, app_html):
    importmap = cdn_tool.read_importmap(app_html)
    assert importmap, "import map not found in app.html"
    return importmap


def test_importmap_is_pinned(importmap):
    assert set(importmap) == {"imports", "integrity"}
    imports = importmap["imports"]
    integrity = importmap["integrity"]
    assert imports
    for spec, url in imports.items():
        # Static package files only (generated bundles like `/+esm` change)
        assert RE_PINNED_URL.match(url), f"{spec}: {url} is not a pinned static file"
        assert url in integrity, f"{spec}: no integrity hash for {url}"
    for url, sri in integrity.items():
        assert RE_PINNED_URL.match(url), url
        assert RE_SRI.match(sri), f"{url}: invalid hash {sri!r}"


def test_importmap_matches_entry_points(cdn_tool, importmap):
    imports = importmap["imports"]
    for spec, target in cdn_tool.ENTRY_POINTS.items():
        assert spec in imports, f"{spec} is missing; run {SCRIPT.name}"
        assert imports[spec].startswith(CDN + target), f"{spec}: run {SCRIPT.name}"


def test_cdn_tags_have_integrity(app_html):
    tags = re.findall(
        r"<(?:link|script)\b[^>]*\b(?:href|src)=\"https?://[^>]*>", app_html
    )
    assert tags
    for tag in tags:
        assert re.search(r'\bintegrity="sha384-[A-Za-z0-9+/]{64}"', tag), tag
        assert 'crossorigin="anonymous"' in tag, tag
        url = re.search(r'(?:href|src)="([^"]+)"', tag).group(1)
        assert RE_PINNED_URL.match(url), url


def test_stylesheet_versions_match_modules(app_html, importmap):
    """A package that provides a module and a stylesheet uses one version."""
    module_versions = dict(
        re.findall(
            r"/npm/((?:@[\w.-]+/)?[\w.-]+)@([\d.]+)/",
            " ".join(importmap["imports"].values()),
        )
    )
    for name, version in re.findall(
        r'<link\b[^>]*href="https://cdn\.jsdelivr\.net/npm/((?:@[\w.-]+/)?[\w.-]+)@([\d.]+)/',
        app_html,
    ):
        if name in module_versions:
            assert module_versions[name] == version, name


@pytest.mark.parametrize(
    "path", sorted(HTDOCS.glob("*.js"), key=str), ids=lambda p: p.name
)
def test_js_imports_use_importmap(cdn_tool, importmap, path):
    if path.name.startswith("wunderbaum."):
        pytest.skip("vendored file")
    code = path.read_text(encoding="utf-8")
    # Dynamic imports must use string literals, so they can be checked here
    for m in re.finditer(r"\bimport\s*\(\s*(.)", code):
        assert m.group(1) in "\"'", f"{path.name}: non-literal dynamic import"
    for spec in cdn_tool.find_imports(code):
        if spec.startswith("./"):
            assert (HTDOCS / spec).is_file(), f"{path.name}: {spec} not found"
        else:
            assert spec in importmap["imports"], (
                f"{path.name}: {spec!r} is not in the import map"
            )
    assert not re.search(r"""(?:from|import)\s*\(?\s*["']https?:""", code), (
        f"{path.name}: import by URL bypasses SRI"
    )


def test_find_imports(cdn_tool):
    code = """
import { a } from "pkg-a";
import * as b from '@scope/pkg-b';
import "./side-effect.js";
export { c } from "../c.js";
const d = await import("pkg-d/sub/file.js");
/* Doc comment: `@context exportName from "module"`. */
const s = "text from",x="y";
import{e as f}from"pkg-e";export*from"pkg-f";
"""
    assert cdn_tool.find_imports(code) == [
        "pkg-a",
        "@scope/pkg-b",
        "./side-effect.js",
        "../c.js",
        "pkg-d/sub/file.js",
        "pkg-e",
        "pkg-f",
    ]


@pytest.mark.parametrize(
    ("version", "rng", "expected"),
    [
        ("6.7.6", "^6.0.0", True),
        ("7.0.0", "^6.0.0", False),
        ("0.2.5", "^0.2.0", True),
        ("0.3.0", "^0.2.0", False),
        ("1.2.9", "~1.2.3", True),
        ("1.3.0", "~1.2.3", False),
        ("1.0.4", "1.0.4", True),
        ("2.0.0", "^1.0.0 || ^2.0.0", True),
        ("1.5.0", ">=1.2.0 <2.0.0", True),
    ],
)
def test_satisfies(cdn_tool, version, rng, expected):
    assert cdn_tool.satisfies(version, rng) is expected
