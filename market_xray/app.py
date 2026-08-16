from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from threading import RLock
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Market X-Ray OS", version="0.1.0")

MARKETS = {
    "NAS100": {"primary": "NQ", "venue": "CME", "asset": "index_futures"},
    "SPX500": {"primary": "ES", "venue": "CME", "asset": "index_futures"},
    "EURUSD": {"primary": "6E", "venue": "CME", "asset": "fx_futures"},
    "GBPUSD": {"primary": "6B", "venue": "CME", "asset": "fx_futures"},
    "XAUUSD": {"primary": "GC", "venue": "COMEX", "asset": "metals"},
    "XAGUSD": {"primary": "SI", "venue": "COMEX", "asset": "metals"},
    "USOIL": {"primary": "CL", "venue": "NYMEX", "asset": "energy"},
    "DXY": {"primary": "DX", "venue": "ICE", "asset": "fx_index"},
    "BTCUSD": {"primary": "BTC", "venue": "MULTI", "asset": "crypto"},
    "ETHUSD": {"primary": "ETH", "venue": "MULTI", "asset": "crypto"},
}

TIMEFRAMES = ["100ms", "1s", "5s", "15s", "30s", "1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]

class Evidence(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    INFERRED = "inferred"
    UNKNOWN = "unknown"

class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"

class EventIn(BaseModel):
    market: str
    ts_ns: int = Field(gt=0)
    kind: Literal["trade", "book_add", "book_cancel", "book_modify", "book_execute", "snapshot", "heartbeat"]
    price: float | None = None
    qty: float | None = Field(default=None, ge=0)
    side: Side | None = None
    sequence: int | None = None
    venue: str | None = None

@dataclass(frozen=True)
class Event:
    market: str
    ts_ns: int
    kind: str
    price: float | None
    qty: float | None
    side: str | None
    sequence: int | None
    venue: str | None

class EventStore:
    """In-memory event log for bootstrap. Production storage will be append-only Parquet/DuckDB."""
    def __init__(self, max_events: int = 500_000) -> None:
        self._events: deque[Event] = deque(maxlen=max_events)
        self._lock = RLock()
        self._last_seq: dict[tuple[str, str], int] = {}
        self.missing_sequences = 0
        self.duplicates = 0
        self.out_of_order = 0

    def append(self, e: Event) -> None:
        key = (e.market, e.venue or "UNKNOWN")
        with self._lock:
            if e.sequence is not None:
                prev = self._last_seq.get(key)
                if prev is not None:
                    if e.sequence == prev:
                        self.duplicates += 1
                    elif e.sequence < prev:
                        self.out_of_order += 1
                    elif e.sequence > prev + 1:
                        self.missing_sequences += e.sequence - prev - 1
                if prev is None or e.sequence > prev:
                    self._last_seq[key] = e.sequence
            self._events.append(e)

    def recent(self, market: str, limit: int) -> list[Event]:
        with self._lock:
            found = [e for e in reversed(self._events) if e.market == market]
            return list(reversed(found[:limit]))

store = EventStore()


def require_market(market: str) -> str:
    market = market.upper()
    if market not in MARKETS:
        raise HTTPException(404, f"Unsupported market: {market}")
    return market


def derive_state(events: list[Event]) -> dict:
    trades = [e for e in events if e.kind == "trade" and e.qty is not None]
    buy = sum(e.qty or 0 for e in trades if e.side == Side.BUY.value)
    sell = sum(e.qty or 0 for e in trades if e.side == Side.SELL.value)
    total = buy + sell
    imbalance = 0.0 if total == 0 else (buy - sell) / total
    if total == 0:
        control = "UNKNOWN"
        evidence = Evidence.UNKNOWN
    elif imbalance >= .25:
        control = "BUYERS"
        evidence = Evidence.DERIVED
    elif imbalance <= -.25:
        control = "SELLERS"
        evidence = Evidence.DERIVED
    else:
        control = "BALANCE"
        evidence = Evidence.DERIVED
    return {
        "control": control,
        "trade_imbalance": round(imbalance, 6),
        "buy_qty": buy,
        "sell_qty": sell,
        "evidence": evidence.value,
        "note": "Bootstrap metric only; not a trading signal.",
    }

@app.get("/api/v1/markets")
def markets():
    return {"markets": MARKETS, "timeframes": TIMEFRAMES}

@app.post("/api/v1/events")
def ingest(event: EventIn):
    market = require_market(event.market)
    e = Event(
        market=market,
        ts_ns=event.ts_ns,
        kind=event.kind,
        price=event.price,
        qty=event.qty,
        side=event.side.value if event.side else None,
        sequence=event.sequence,
        venue=event.venue or MARKETS[market]["venue"],
    )
    store.append(e)
    return {"accepted": True}

@app.get("/api/v1/xray/{market}")
def xray(market: str, limit: int = 5000):
    market = require_market(market)
    events = store.recent(market, min(max(limit, 1), 100_000))
    return {
        "market": market,
        "instrument": MARKETS[market],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(events),
        "state": derive_state(events),
        "data_health": {
            "missing_sequences": store.missing_sequences,
            "duplicates": store.duplicates,
            "out_of_order": store.out_of_order,
            "verified": store.missing_sequences == 0 and store.out_of_order == 0,
        },
    }

@app.get("/api/v1/replay/{market}")
def replay(market: str, limit: int = 1000):
    market = require_market(market)
    return {"market": market, "events": [asdict(e) for e in store.recent(market, min(limit, 20_000))]}

@app.get("/health")
def health():
    return {"status": "ok", "service": "market-xray", "version": app.version}
