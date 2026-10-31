import pytest
import webtest

from wsgidav import util
from wsgidav.dav_error import DAVError
from wsgidav.wsgidav_app import WsgiDAVApp


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/./private/secret.txt", "/private/secret.txt"),
        ("/.//private/secret.txt", "/private/secret.txt"),
        ("/foo/../private/secret.txt", "/private/secret.txt"),
        ("/private/", "/private/"),
        ("//", "/"),
    ],
)
def test_normalize_path(path, expected):
    assert util.normalize_path(path) == expected


def test_normalize_path_rejects_escape():
    with pytest.raises(DAVError) as error:
        util.normalize_path("/../../private/secret.txt")
    assert error.value.value == 400


def test_normalized_path_selects_nested_share(tmp_path):
    (tmp_path / "private").mkdir()
    app = WsgiDAVApp({
        "provider_mapping": {
            "/": str(tmp_path),
            "/private": str(tmp_path / "private"),
        },
        "middleware_stack": [],
        "logging": {"enable_loggers": []},
    })

    share, _provider = app.resolve_provider(util.normalize_path("/./private/file"))

    assert share == "/private"


@pytest.mark.parametrize("method", ["copy", "move"])
@pytest.mark.parametrize(
    "mount_path,destination",
    [(None, "/private/target.txt"), ("/dav", "/dav/private/target.txt")],
)
def test_copy_move_cannot_write_into_nested_share(
    tmp_path, method, mount_path, destination
):
    root = tmp_path / "root"
    private = root / "private"
    private.mkdir(parents=True)
    (root / "source.txt").write_text("source")
    (private / "target.txt").write_text("protected")
    app = WsgiDAVApp({
        "simple_dc": {"user_mapping": {"*": True}},  # anonymous access
        "provider_mapping": {
            "/": str(root),
            "/private": {"root": str(private), "readonly": True},
        },
        "mount_path": mount_path,
        "logging": {"enable_loggers": []},
    })
    client = webtest.TestApp(app)

    response = client.request(
        "/source.txt",
        headers={"Destination": destination},
        method=method.upper(),
        status=502,
    )

    assert response.status_int == 502
    assert (private / "target.txt").read_text() == "protected"
    assert not (private / "source.txt").exists()
