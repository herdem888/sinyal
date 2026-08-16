# MARKET X-RAY OS — MASTER SPEC v0.1

## Mission
Reconstruct what is observable behind price movement without presenting inference as fact. Live and historical replay must use the same event-processing path.

## Watchlist
NAS100, SPX500, EURUSD, GBPUSD, XAUUSD, XAGUSD, USOIL, DXY, BTCUSD, ETHUSD.

## Truth classes
- OBSERVED: directly present in an acquired feed.
- DERIVED: deterministic calculation from observed data.
- INFERRED: model/statistical interpretation.
- UNKNOWN: not observable or insufficient evidence.

## Hard rules
1. No BUY/SELL claim may bypass data-health gates.
2. Missing/out-of-order sequence state is visible.
3. Live/replay parity is mandatory.
4. No look-ahead in replay/research.
5. Every derived state carries provenance/version metadata.
6. Market-specific baselines; never normalize all instruments as one market.
7. No claim of knowing participant identity or intent without direct evidence.

## Architecture
Feed adapters -> immutable raw event log -> validation/time sync -> normalized event bus -> book builders -> feature engines -> timeframe aggregators -> regime/context -> evidence/state engine -> replay/research -> API/WebSocket -> UI.

## Planned engines
Order lifecycle; MBO/MBP book; trades/aggressor flow; queue depletion/refill; liquidity age/survival/migration; sweep depth; absorption/exhaustion; OFI; delta/CVD; spread/mid/microprice; depth/slope; price impact; effort-vs-result; resilience; liquidity vacuum; momentum/acceleration; volatility/liquidity regimes; market phase; multi-timeframe propagation/conflict; cross-market/breadth; anomaly/change-point; historical twins/anti-twins; scenario distributions; MFE/MAE; edge decay; execution/slippage/fill simulation; calibration/drift; autopsy; event search.

## UI modes
NORMAL, X-RAY, MICROSCOPE, MRI/HEATMAP, AUTOPSY, REPLAY, DATA COMMAND CENTER, RESEARCH LAB, GLOBAL MATRIX.

## Data health
Expected/received/parsed/applied, missing, duplicate, out-of-order, corrupt, stale, snapshot mismatch, clock drift, latency p50/p95/p99, book sync, recovery state, schema version, source fingerprint.

## Acceptance philosophy
A feature is not complete because it renders. It needs deterministic tests, replay tests, failure-path tests, provenance, and where statistical: chronological OOS validation. `INCONCLUSIVE` is a valid result.

## Bootstrap status
Phase 0 starts with instrument registry, normalized event ingestion, sequence-health accounting, simple derived trade imbalance, replay endpoint, and tests. This metric is explicitly not a trading signal.
