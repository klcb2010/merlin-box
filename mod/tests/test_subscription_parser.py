import importlib.util
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "sub2box" / "main.py"
SPEC = importlib.util.spec_from_file_location("sub2box_main", MODULE_PATH)
sub2box = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sub2box)


class FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise sub2box.requests.HTTPError(f"HTTP {self.status_code}")


def test_subscription_url_keeps_jpg_suffix_and_route_query():
    url = "https://sub.example.invalid/hidden.jpg?route=1&token=a%2Fb"
    first = FakeResponse(403, "")
    second = FakeResponse(200, "ss://example")
    with patch.object(sub2box.requests, "get", side_effect=[first, second]) as request:
        assert sub2box.fetch_subscription(url) == "ss://example"
    assert request.call_count == 2
    assert request.call_args_list[0].args[0] == url
    assert request.call_args_list[1].args[0] == url
    assert request.call_args_list[0].kwargs["headers"]["User-Agent"] == "clash.meta"


def test_anytls_uri_converts_to_singbox_outbound():
    sub2box.is_local_ip = lambda _host: False
    outbound = sub2box.parse_uri(
        "anytls://p%40ssword@example.invalid:8443?sni=edge.example#节点%20A"
    )
    assert outbound["type"] == "anytls"
    assert outbound["tag"] == "节点 A"
    assert outbound["server"] == "example.invalid"
    assert outbound["server_port"] == 8443
    assert outbound["password"] == "p@ssword"
    assert outbound["tls"] == {
        "enabled": True,
        "server_name": "edge.example",
    }



def test_anytls_uri_defaults_port_and_sni():
    sub2box.is_local_ip = lambda _host: False
    outbound = sub2box.parse_uri("anytls://secret@example.invalid#Default")
    assert outbound["type"] == "anytls"
    assert outbound["server_port"] == 443
    assert outbound["password"] == "secret"
    assert outbound["tls"]["server_name"] == "example.invalid"


def test_anytls_uri_rejects_missing_password():
    sub2box.is_local_ip = lambda _host: False
    assert sub2box.parse_uri("anytls://@example.invalid:443#Broken") is None


def test_clash_yaml_anytls_nodes_convert_with_tls_options():
    sub2box.is_local_ip = lambda _host: False
    content = """
mixed-port: 7890
allow-lan: true
proxies:
  - name: "Hong Kong 01"
    type: anytls
    server: node.example.invalid
    port: "601"
    password: "sample-secret"
    udp: true
    client-fingerprint: chrome
    sni: edge.example.invalid
    skip-cert-verify: true
proxy-groups:
  - name: SSRDOG
    type: select
    proxies: ["Hong Kong 01"]
"""
    outbounds = sub2box.parse_clash_yaml(content)
    assert len(outbounds) == 1
    outbound = outbounds[0]
    assert outbound["type"] == "anytls"
    assert outbound["tag"] == "Hong Kong 01"
    assert outbound["server_port"] == 601
    assert outbound["password"] == "sample-secret"
    assert outbound["tls"]["server_name"] == "edge.example.invalid"
    assert outbound["tls"]["insecure"] is True
    assert outbound["tls"]["utls"]["fingerprint"] == "chrome"


def test_clash_yaml_without_proxies_is_not_misidentified():
    assert sub2box.parse_clash_yaml("mixed-port: 7890\nmode: rule\n") is None
