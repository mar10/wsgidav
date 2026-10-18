# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""Tests for XML parsing helpers."""

from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, skipUnless

from wsgidav import util, xml_tools


@skipUnless(xml_tools.use_lxml, "Requires lxml")
class XmlEntityResolutionTest(TestCase):
    def test_string_to_xml_does_not_resolve_external_entities(self):
        with TemporaryDirectory() as temp_dir:
            secret = "external entity content"
            secret_file = Path(temp_dir) / "secret.txt"
            secret_file.write_text(secret, encoding="utf-8")
            xml = (
                f'<!DOCTYPE root [<!ENTITY xxe SYSTEM "{secret_file.as_uri()}">]>'
                "<root>&xxe;</root>"
            )

            root = xml_tools.string_to_xml(xml)

            self.assertNotIn(secret, xml_tools.xml_to_bytes(root).decode("utf-8"))

    def test_parse_xml_body_does_not_resolve_external_entities(self):
        with TemporaryDirectory() as temp_dir:
            secret = "external entity content"
            secret_file = Path(temp_dir) / "secret.txt"
            secret_file.write_text(secret, encoding="utf-8")
            request_body = (
                f'<!DOCTYPE root [<!ENTITY xxe SYSTEM "{secret_file.as_uri()}">]>'
                "<root>&xxe;</root>"
            ).encode()
            environ = {
                "CONTENT_LENGTH": str(len(request_body)),
                "wsgi.input": BytesIO(request_body),
            }

            root = util.parse_xml_body(environ)

            self.assertNotIn(secret, xml_tools.xml_to_bytes(root).decode("utf-8"))
