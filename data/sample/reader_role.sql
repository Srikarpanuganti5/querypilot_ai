-- Run as the table owner/admin in the target database, AFTER migrations.
-- Supply reader_password as a psql variable from a local secret. Never commit its value.
-- One-time provisioning. For rotation, ALTER ROLE separately with the admin account.
CREATE ROLE querypilot_reader LOGIN PASSWORD :'reader_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database()) \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO querypilot_reader', current_database()) \gexec
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO querypilot_reader;
GRANT SELECT ON public.customers, public.products, public.orders,
    public.order_items, public.payments, public.refunds TO querypilot_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO querypilot_reader;
ALTER ROLE querypilot_reader SET default_transaction_read_only = on;
ALTER ROLE querypilot_reader SET statement_timeout = '5s';
ALTER ROLE querypilot_reader SET lock_timeout = '2s';
