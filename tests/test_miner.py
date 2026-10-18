"""The miner page against a real Green node."""

import json
import socket
import time
import urllib.error
import urllib.request

import pytest

from green.chain import make_genesis
from green.crypto import Key
from green.node import Node
from green_miner.miner import Miner


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_until(cond, what, timeout=60):
    end = time.time() + timeout
    while not cond():
        assert time.time() < end, f"timed out waiting for {what}"
        time.sleep(0.1)


def call(ui, path, body=None, token=True, headers=None):
    h = {"Content-Type": "application/json", **({"X-UI-Token": ui.token} if token else {}), **(headers or {})}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(ui.url + path, data=data, headers=h, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read()) if path != "/" else r.read()


def refused(ui, path, **kw) -> tuple[int, str]:
    with pytest.raises(urllib.error.HTTPError) as e:
        call(ui, path, **kw)
    return e.value.code, json.loads(e.value.read()).get("error", "")


@pytest.fixture
def node(tmp_path):
    miner = Key.generate()
    n = Node(str(tmp_path / "node"), make_genesis(miner.address, "ui"), port=free_port(), miner_key=miner,
             log=lambda m: None)
    n.start(mine=True)
    yield n
    n.stop()


def test_the_miner_page_steers_the_node(node):
    m = Miner(node.url, port=0)
    m.start()
    try:
        st = call(m, "/api/state", token=False)
        assert st["mining"] and st["miner"] == node.miner_key.address and st["blocks_found"] >= 0
        assert call(m, "/api/mining", body={"intensity": 30})["intensity"] == 30 and node.intensity == 30
        assert call(m, "/api/mining", body={"on": False})["mining"] is False and not node.mining
        r = call(m, "/api/mining", body={"gpu": True})
        assert (r["gpu"] is not None) == (node.gpu is not None)
        call(m, "/api/mining", body={"on": True, "gpu": False})
        assert node.mining and node.gpu is None
        assert refused(m, "/api/mining", body={})[0] == 400
        assert refused(m, "/api/mining", body={"intensity": 0})[0] == 400      # the node refuses it
    finally:
        m.stop()



def test_web_pages_cannot_use_the_miner(node):
    m = Miner(node.url, port=0)
    m.start()
    try:
        assert refused(m, "/api/mining", body={"on": False}, token=False)[0] == 403
        assert refused(m, "/api/mining", body={"on": False}, headers={"Host": "evil.example"})[0] == 403
        assert refused(m, "/", token=False, headers={"Host": "evil.example"})[0] == 403
        assert node.mining
    finally:
        m.stop()
