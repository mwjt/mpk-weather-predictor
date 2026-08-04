SELECT 'CREATE USER reader' WHERE NOT EXISTS (
    SELECT FROM pg_catalog.pg_roles WHERE rolname = 'reader'
)\gexec

ALTER USER reader WITH PASSWORD :'reader_password';

GRANT CONNECT ON DATABASE mpk_harvester TO reader;
GRANT USAGE ON SCHEMA public TO reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO reader;