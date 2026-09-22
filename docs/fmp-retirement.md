# Financial-data provider retirement

The FMP `FundamentalDataNode`, `fmp_api` credential template, provider transport,
synthetic fixtures, provider-specific replay adapter and two FMP examples are
removed at the owner's request. Other external credentials, Telegram delivery
guards, generic HTTP requests and financial-analysis plugins remain supported.

Use `OverseasStockFundamentalNode` through an `OverseasStockBrokerNode` for LS
security-detail PER/EPS. The SDK source is `g3104/blocks.py`; its example uses
`delaygb=R`, `keysymbol`, `exchcd` and `symbol`. The existing executor reads
`perv` and `epsv` into `per` and `eps`. This is not a guarantee of populated
broker fields. A positive-PER filter must reject missing/nonfinite/zero/negative
values. The SDK does not establish PER computation basis or market-cap units.

This is not a drop-in schema substitution. LS uses `value`/`values` rather than
`data`/`summary`, and does not supply statement history, free cash flow, ROE or
PBR through this node. Piotroski/DCF/MagicFormula still require their documented
inputs from verified sources. No fabricated substitute values are allowed.

Old graphs receive an actionable unknown-node validation error. Customer
definitions, credentials, drafts and running executions are not rewritten or
deleted. Replacing a node requires rebinding and validating the affected graph.
The September22 read-only audit found no saved prod graph or credential using
FMP, but one unfinished prod draft; preserve that draft as repair input.

All four 2.0.1 packages are published on TestPyPI and PyPI with matching artifact
hashes. Installed-wheel checks passed176 cases. Application rollout remains a
release candidate until installed runtime packages,
registration API, node catalog and retrieval documents are checked together.

The release uses major version2.0.1 because a public node and credential contract
are removed. All four packages move together to avoid incompatible dependency
ranges; Finance changes only its Core dependency. The separate node-by-node
workspace/replay feature is not included in this public release.
