from urllib.parse import quote

from app.core.enums import TonNetwork


def tonscan_transaction_url(transaction_hash: str, network: TonNetwork) -> str:
    """Build a network-aware Tonscan URL for a confirmed transaction."""
    host = "testnet.tonscan.org" if network is TonNetwork.TESTNET else "tonscan.org"
    return f"https://{host}/tx/{quote(transaction_hash, safe='')}"
