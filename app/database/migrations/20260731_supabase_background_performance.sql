begin;

-- Supports reconciliation scans filtered by flow and the two active states.
-- The partial predicate keeps the index small as completed ledger rows grow.
create index if not exists financial_operations_reconciliation_idx
    on public.financial_operations(flow, status, id)
    where status in ('prepared', 'submitted');

commit;

notify pgrst, 'reload schema';
