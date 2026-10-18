"""The Green miner: a page in the browser to watch and steer a mining node.

    python -m green_miner.miner [--node URL] [--port 8620]

Start and stop mining, choose how much of the time the hardware works (intensity),
mine on the GPU or the CPU, and watch the speed, the blocks and shares found and
what they earned. The node must run on this computer (its mining switch only answers
from here): `grn node --mine --gpu`.
"""

import argparse
import threading
import time
import webbrowser
from collections import deque

from green import params
from green.node import http_get, http_post

from .server import LocalUI, UIError


class Miner(LocalUI):
    def __init__(self, node: str, port: int = 8620):
        super().__init__("miner.html", port, "Green miner")
        self.node = node.rstrip("/")
        self.samples: deque = deque(maxlen=720)          # (time, balance, units): the last hour at 5 s
        self.lock = threading.Lock()

    def get_state(self, q: dict) -> dict:
        st = http_get(f"{self.node}/status", timeout=5)
        out = {"node": self.node, "height": st["height"], "mining": st["mining"], "gpu": st.get("gpu"),
               "intensity": st.get("intensity", 100), "units_per_second": st["units_per_second"],
               "units_per_block": st["units_per_block"], "peers": len(st["peers"]), "miner": st["miner"],
               "blocks_found": st["stats"].get("blocks_found", 0), "shares_found": st["stats"].get("shares_found", 0),
               "units": st["stats"].get("units", 0), "useful_units": st["stats"].get("useful_units", 0),
               "next_emission": st.get("next_emission"), "seconds_per_block": params.TARGET_BLOCK_SECONDS}
        if st["miner"]:
            acct = http_get(f"{self.node}/account/{st['miner']}", timeout=5)
            out["balance"] = acct["balance"]
            now = time.time()
            with self.lock:
                if not self.samples or now - self.samples[-1][0] >= 5:
                    self.samples.append((now, acct["balance"], out["units"]))
                old = next((s for s in self.samples if now - s[0] <= 600), self.samples[0])
            span = max(1.0, now - old[0])
            out["earned_per_hour"] = int((acct["balance"] - old[1]) * 3600 / span) if span >= 30 else None
            # Expected blocks per hour from our share of the work: our units vs the units a block needs.
            if st["units_per_block"]:
                out["expected_blocks_per_hour"] = round(st["units_per_second"] * 3600 / st["units_per_block"], 2)
        return out

    def post_mining(self, body: dict) -> dict:
        req = {k: body[k] for k in ("on", "intensity", "gpu") if k in body}
        if not req:
            raise UIError("nothing to change")
        if "intensity" in req:
            req["intensity"] = int(req["intensity"])
        return http_post(f"{self.node}/mining", req, timeout=60)     # (turning the GPU on checks it first)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m green_miner.miner", description="The Green miner, in a browser")
    ap.add_argument("--node", default=f"http://127.0.0.1:{params.DEFAULT_PORT}", help="the mining node's API (on this computer)")
    ap.add_argument("--port", type=int, default=8620)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args(argv)
    m = Miner(args.node, args.port)
    m.start()
    print(f"Green miner: {m.url}   (node {args.node}); Ctrl+C to stop the page (the node keeps mining)")
    if not args.no_browser:
        webbrowser.open(m.url)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        m.stop()


if __name__ == "__main__":
    main()
