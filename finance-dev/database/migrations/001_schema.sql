-- Finance DEv schema. Run in the Supabase SQL editor (or `supabase db push`), then run 002_rls.sql.
-- Requires Postgres 15+ (Supabase default) for ON DELETE SET NULL (column).

create table public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  full_name   text check (char_length(full_name) <= 100),
  currency    text not null default 'ZAR' check (currency ~ '^[A-Z]{3}$'),
  role        text not null default 'user' check (role in ('user', 'admin')),
  created_at  timestamptz not null default now()
);

create table public.income_categories (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  name        text not null check (char_length(name) between 1 and 60),
  created_at  timestamptz not null default now(),
  unique (user_id, name),
  unique (user_id, id)
);

create table public.expense_categories (like public.income_categories including all);
alter table public.expense_categories
  add constraint expense_categories_user_id_fkey foreign key (user_id) references auth.users (id) on delete cascade;

create table public.transactions (
  id                   uuid primary key default gen_random_uuid(),
  user_id              uuid not null default auth.uid() references auth.users (id) on delete cascade,
  type                 text not null check (type in ('income', 'expense')),
  amount               numeric(14,2) not null check (amount > 0),
  tx_date              date not null default current_date,
  description          text check (char_length(description) <= 200),
  income_category_id   uuid,
  expense_category_id  uuid,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  -- composite FKs: a transaction can only point at a category owned by the same user
  foreign key (user_id, income_category_id)  references public.income_categories (user_id, id)
    on delete set null (income_category_id),
  foreign key (user_id, expense_category_id) references public.expense_categories (user_id, id)
    on delete set null (expense_category_id),
  check ((type = 'income' and expense_category_id is null) or (type = 'expense' and income_category_id is null))
);

create table public.budgets (
  id                   uuid primary key default gen_random_uuid(),
  user_id              uuid not null default auth.uid() references auth.users (id) on delete cascade,
  expense_category_id  uuid not null,
  month                date not null check (month = date_trunc('month', month)::date),
  amount_limit         numeric(14,2) not null check (amount_limit > 0),
  created_at           timestamptz not null default now(),
  foreign key (user_id, expense_category_id) references public.expense_categories (user_id, id) on delete cascade,
  unique (user_id, expense_category_id, month)
);

create table public.financial_reports (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null default auth.uid() references auth.users (id) on delete cascade,
  month           date not null check (month = date_trunc('month', month)::date),
  total_income    numeric(14,2) not null default 0,
  total_expenses  numeric(14,2) not null default 0,
  balance         numeric(14,2) not null default 0,
  generated_at    timestamptz not null default now(),
  unique (user_id, month)
);

create table public.audit_logs (
  id          bigint generated always as identity primary key,
  user_id     uuid references auth.users (id) on delete set null,
  action      text not null,
  table_name  text not null,
  record_id   uuid,
  created_at  timestamptz not null default now()
);

-- Indexes
create index transactions_user_date_idx on public.transactions (user_id, tx_date desc);
create index transactions_user_type_idx on public.transactions (user_id, type);
create index budgets_user_month_idx     on public.budgets (user_id, month);
create index audit_logs_user_idx        on public.audit_logs (user_id, created_at desc);

-- Triggers ---------------------------------------------------------------
create function public.set_updated_at() returns trigger language plpgsql
set search_path = '' as $$
begin new.updated_at = now(); return new; end $$;
create trigger transactions_updated before update on public.transactions
  for each row execute function public.set_updated_at();

-- Audit trail is written by the database, so clients cannot skip or forge it.
create function public.audit_row() returns trigger language plpgsql security definer
set search_path = '' as $$
begin
  insert into public.audit_logs (user_id, action, table_name, record_id)
  values (auth.uid(), tg_op, tg_table_name, coalesce(new.id, old.id));
  return coalesce(new, old);
end $$;
create trigger transactions_audit after insert or update or delete on public.transactions
  for each row execute function public.audit_row();
create trigger budgets_audit after insert or update or delete on public.budgets
  for each row execute function public.audit_row();

-- New sign-up -> profile + starter categories
create function public.handle_new_user() returns trigger language plpgsql security definer
set search_path = '' as $$
begin
  insert into public.profiles (id, full_name)
  values (new.id, left(new.raw_user_meta_data ->> 'full_name', 100));
  insert into public.income_categories (user_id, name)
    select new.id, n from unnest(array['Salary','Business','Investments','Gifts','Other income']) n;
  insert into public.expense_categories (user_id, name)
    select new.id, n from unnest(array['Housing','Groceries','Transport','Utilities','Health',
                                       'Education','Entertainment','Airtime & data','Other expenses']) n;
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

revoke execute on function public.audit_row(), public.handle_new_user(), public.set_updated_at()
  from public, anon, authenticated;
