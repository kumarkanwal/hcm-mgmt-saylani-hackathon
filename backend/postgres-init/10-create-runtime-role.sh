#!/bin/sh
set -eu

psql --set=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=db_name="$POSTGRES_DB" \
  --set=db_owner="$POSTGRES_USER" \
  --set=app_password="$POSTGRES_APP_PASSWORD" <<'SQL'
CREATE ROLE hcm_lite_runtime
    LOGIN PASSWORD :'app_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE :"db_name" TO hcm_lite_runtime;
GRANT USAGE ON SCHEMA public TO hcm_lite_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hcm_lite_runtime;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO hcm_lite_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE :"db_owner" IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hcm_lite_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE :"db_owner" IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO hcm_lite_runtime;
SQL
