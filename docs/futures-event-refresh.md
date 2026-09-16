# Futures fill notifications and account refresh

SDK synchronous websocket callbacks run on a worker thread. Workflow PnL
notifications must return to the workflow event loop before creating tasks.
Callbacks received during shutdown are discarded without creating coroutines.
This applies to stock, futures and domestic PnL listeners.

The futures tracker listens to both TC2 confirmations (`svc_id=HO02`) and
TC3 fills (`svc_id=CH01`). A delayed refresh coalesces bursts. Events during a
read request a serial follow-up; periodic and event reads share a lock. Stop
cancels the owned refresh and removes only this tracker's callbacks.

Standalone TC3 records preserve the explicitly supplied `crncy_cd`. Missing
currency stays unknown. This does not change managed TC3 identity verification,
prove REST/TC3 fill-number equivalence or enable futures FIFO monetary results.

## Validation

179 focused engine/SDK tests cover actual response models, broker-thread
callbacks, coalescing, concurrent reads, shutdown, currency and existing managed
fill guards. HKEX paper verification observed actual buy/sell TC3 messages and
standalone ledger ingestion. A later pending order was cancelled and confirmed
through linked REST history; TC2 delivery was not observed in that attempt.
No live order was submitted. Community ingestion and complete futures workflow
monetary accounting remain separate verification work.
