from urllib.parse import quote

from app.core.enums import TonNetwork


def tonviewer_transaction_url(transaction_hash: str, network: TonNetwork) -> str:
    """Build a network-aware Tonviewer URL for a confirmed transaction."""
    host = "testnet.tonviewer.com" if network is TonNetwork.TESTNET else "tonviewer.com"
    return f"https://{host}/transaction/{quote(transaction_hash, safe='')}"
