# Version 2.6.2 release candidate validation

Core and engine prepare 2.6.2 together. The engine requires core ^2.6.2;
finance2.0.1 and community2.3.1 remain unchanged. This source candidate is not
yet published and does not prove that any hosted consumer uses it.

The [futures history contract](futures-minute-alias-contract.md) describes the
limited correction: canonical minute aliases use the existing single-page
o3103 path. Unsupported hourly periods and rollover adjustment are rejected.
Pagination, complete-range coverage and candle finality are not added.

Local Python3.12 checks import the built wheel files, rather than this checkout:

- Engine:185 existing and new focused cases passed, including actual SDK
  request-model assertions, static validation, early rejection, stock interval
  guards, structured errors and per-symbol iteration.
- Core:828 metadata, schema, localization and version cases passed. One existing
  `test_metadata_has_required_shape[OverseasStockHistoricalDataNode]` failure
  requires two examples, while the published2.6.1 stock node has one. The same
  test fails identically against the unchanged published2.6.1 wheel. No test
  expectation or unrelated stock example was changed for this release.
- Broker requests are synthetic and intercepted; the offline network guard is
  installed before runtime imports. No broker, customer or model action.
- Core and engine wheel/sdist source and metadata are inspected. The engine lock
  changes only core and its two artifact hashes; the other100 locked packages
  are unchanged. Root/core lock files need no dependency change and remain fresh.

The engine lock initially contains hashes of the locally built core candidate.
Before engine publication, the release owner must verify the merged-source core
build and published PyPI artifacts match these hashes. A mismatch requires a
reviewed lock correction; it is not permission to overwrite a published version.
Tags must refer to the reviewed merged main commit. Finance/community are not
rebuilt or published for this correction.

Publication, clean installation from the package index and coordinated consumer
adoption remain separate gates. AI and dedicated replay must use matching actual
runtime identities, and catalog entries must be prepared for that identity.
Existing2.6.1 source pins or receipts do not certify the new implementation.
Desktop installation and hosted Linux acceptance are not covered by these local
macOS tests. No private strategy corpus or database contents are included in the
public package.
