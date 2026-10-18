# Green Miner

A miner for [Green (GRN)](https://github.com/ErtungaYusuf/green), a page in your browser. It runs on your computer, listens only on `127.0.0.1`, and steers a Green node's mining. The wallet is a separate program: [green-wallet](https://github.com/ErtungaYusuf/green-wallet).

## Install

Python 3.11 or newer, with Green installed (the green repository next to this one works too):

```bash
pip install -e ../green
pip install -e ".[dev]"
```

## The miner

```bash
green-miner --node http://127.0.0.1:8545
```

Start and stop mining, set the intensity (the share of the time the GPU or CPU works; the rest it rests), switch between GPU and CPU while running, and watch the speed, blocks and shares found, and what they earn. The node must run on this computer, with a wallet: `grn node --mine --gpu`. On a local network (`grn localnet start`), point it at a miner's node: `green-miner --node http://127.0.0.1:18501` (alice).

## Safety

The page only answers requests that name this computer (`Host: 127.0.0.1` or `localhost`), so a DNS-rebinding web page cannot reach it, and every action needs the page's own token, which a web site open in another tab can neither read nor send. Anyone who can run programs on your computer can still use it.

## Tests

```bash
python -m pytest -q
```

They start a real mining Green node and check steering it from the page, and that web pages from other sites cannot.
