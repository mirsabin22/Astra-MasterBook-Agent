CREATE TABLE outlet_scope (
  outlet_id TEXT NOT NULL PRIMARY KEY,
  main_dealer_code TEXT NOT NULL,
  sales_owner TEXT NOT NULL
);
CREATE INDEX idx_scope_sales ON outlet_scope(sales_owner);
CREATE INDEX idx_scope_md ON outlet_scope(main_dealer_code);

CREATE TABLE followup_current (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  outlet_id TEXT NOT NULL UNIQUE,
  sales_owner TEXT NOT NULL,
  status TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  next_followup TEXT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX idx_fc_sales_next ON followup_current(sales_owner, next_followup);

CREATE TABLE followup_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  current_id INTEGER NOT NULL,
  outlet_id TEXT NOT NULL,
  sales_owner TEXT NOT NULL,
  status TEXT NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  next_followup TEXT NULL,
  version INTEGER NOT NULL,
  changed_at TEXT NOT NULL
);
CREATE INDEX idx_fh_current ON followup_history(current_id, version);
CREATE INDEX idx_fh_outlet ON followup_history(outlet_id);

CREATE TABLE main_dealers (
  code TEXT NOT NULL PRIMARY KEY,
  name TEXT NOT NULL,
  territory TEXT NULL,
  provinces TEXT NULL
);

CREATE TABLE outlets (
  id TEXT NOT NULL PRIMARY KEY,
  name TEXT NOT NULL,
  main_dealer_code TEXT NOT NULL,
  dealer_code TEXT NULL,
  address TEXT NULL,
  city TEXT NULL,
  province TEXT NULL,
  services TEXT NULL,
  whatsapp TEXT NULL,
  phone TEXT NULL,
  company_id TEXT NULL
);
CREATE INDEX idx_outlets_md ON outlets(main_dealer_code);
CREATE INDEX idx_outlets_prov ON outlets(province);

CREATE TABLE telegram_users (
  telegram_id INTEGER NOT NULL PRIMARY KEY,
  identity TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('sales','management')),
  active INTEGER NOT NULL DEFAULT 1,
  added_by TEXT NULL,
  added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE report_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job TEXT NOT NULL,
  period TEXT NOT NULL,
  status TEXT NOT NULL,
  ran_at TEXT NOT NULL,
  UNIQUE (job, period)
);