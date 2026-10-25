import pytest

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
    app = WsgiDAVApp(
        {
            "provider_mapping": {
                "/": str(tmp_path),
                "/private": str(tmp_path / "private"),
            },
            "middleware_stack": [],
            "logging": {"enable_loggers": []},
        }
    )

    share, _provider = app.resolve_provider(util.normalize_path("/./private/file"))

    assert share == "/private"
