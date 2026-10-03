# Version 2.6.0 integration validation

The feature branch includes current origin/main (31ea3823) without dropping
historical-cost recovery or scheduler fixes. Engine and core move together to
2.6.0; finance 2.0.1 and community 2.3.1 stay unchanged.

Validation on Python 3.12 in the isolated Linux candidate:
- 55 engine regression modules: 1294 passed, one existing failure.
- Core schema, localization, connection, version and calendar checks: 895 passed.
- The existing failure is test_replay_mapping_reports.py::
  test_report_computes_drawdown_from_actual_equity_series. The same test fails
  against the unchanged v2.5.6 source in the same container (nine related cases
  pass). No new engine regression was observed in this selected gate.
- New metadata examples meet the shared schema contract; expected registry size
  is 72 core plus two community nodes. XHKG is now an explicit supported enum.
- Offline tests deny broker/network access. No real orders or customer edits.

The historical report failure remains separate work. Passing fixtures do not
prove every strategy or broker condition. Production service deployment, catalog
publication and desktop installers are separate from the SDK package release.
