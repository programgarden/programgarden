# Version 2.6.3 release candidate validation

The candidate is based on merged upstream 2.6.2. It prepares engine 2.6.3 and
finance 2.0.2; core 2.6.2 and community 2.3.1 are unchanged. The engine finance
requirement is raised to ^2.0.2 so CIDBQ02400 preserves the RecCnt input field.
This document does not establish package publication or hosted installation.

The [paper query contract](paper-futures-business-date.md) describes the narrowly
scoped compatibility correction. Paper startup, pending-order and legacy fill
inquiries use fresh account-scoped broker date evidence. Live-account behavior
and the previously released stock and futures history corrections are retained.
Missing raw blocks, scope changes, expired dates and partial pages stay errors.
No fallback to the machine date or to an invented empty order list is added.

Local Python 3.12 verification imports candidate wheel files, with network access
blocked before runtime imports:

- 368 engine checks cover paper dates, startup evidence, pending/fill behavior,
  order failure reporting, managed lifecycle paths, and existing stock/futures
  history and authoring contracts.
- 62 finance checks cover real SDK model fields, sync/async request serialization,
  response-presence handling and futures history.
- Wheel and sdist package bytes match the corresponding public source files.
  Both builds are reproducible with the recorded source timestamp. Package
  members are allowlisted; no private strategy corpus or customer payload is
  included.
- The engine lock changes only finance's version and two artifact hashes; the
  other 100 packages are unchanged. Root, finance and engine locks remain fresh.
  Installation metadata has no broken dependency requirements.

The engine lock initially binds locally built finance artifacts. Before engine
publication, verify that the reviewed merged-source finance build and published
artifacts match those hashes. If they differ, reconcile the lock and review it
before publishing the engine; never overwrite a published version. Tag the
merged main commit. Do not rebuild or republish unchanged core/community.

Live broker requests, orders and account changes were not performed for this
release preparation. The documented incident observation covers only its actual
query filters. Additional query variants have offline coverage, not a claim of
new live verification. Package publication, clean index installation, dev/prod
consumer verification and desktop packaging remain separate release steps.
