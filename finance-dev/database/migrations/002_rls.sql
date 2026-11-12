-- Row Level Security: users can only touch their own rows.
alter table public.profiles           enable row level security;
alter table public.income_categories  enable row level security;
alter table public.expense_categories enable row level security;
alter table public.transactions       enable row level security;
alter table public.budgets            enable row level security;
alter table public.financial_reports  enable row level security;
alter table public.audit_logs         enable row level security;

revoke all on all tables in schema public from anon;

create policy "own profile read"   on public.profiles for select to authenticated using (id = (select auth.uid()));
create policy "own profile update" on public.profiles for update to authenticated
  using (id = (select auth.uid())) with check (id = (select auth.uid()));
-- users may change their name only, never their role
revoke update on public.profiles from authenticated;
grant  update (full_name) on public.profiles to authenticated;

create policy "own rows" on public.income_categories  for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy "own rows" on public.expense_categories for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy "own rows" on public.transactions       for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy "own rows" on public.budgets            for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy "own rows" on public.financial_reports  for all to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

-- audit logs: read your own, never write (the trigger writes them)
create policy "own audit read" on public.audit_logs for select to authenticated
  using (user_id = (select auth.uid()));
revoke insert, update, delete on public.audit_logs from authenticated;
