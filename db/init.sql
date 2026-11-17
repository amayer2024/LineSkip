-- Idempotent: safe to run on every `docker compose up`.
-- sqlcmd variables PASSES_PWD and ANALYTICS_PWD are passed with -v.
-- One database and one login per service; each login reaches only its own database.
IF DB_ID('passes')    IS NULL CREATE DATABASE passes;
IF DB_ID('analytics') IS NULL CREATE DATABASE analytics;
GO

IF SUSER_ID('passes_user')    IS NULL CREATE LOGIN passes_user    WITH PASSWORD = '$(PASSES_PWD)',    CHECK_POLICY = OFF;
IF SUSER_ID('analytics_user') IS NULL CREATE LOGIN analytics_user WITH PASSWORD = '$(ANALYTICS_PWD)', CHECK_POLICY = OFF;
GO

USE passes;
GO
IF USER_ID('passes_user') IS NULL CREATE USER passes_user FOR LOGIN passes_user;
ALTER ROLE db_ddladmin  ADD MEMBER passes_user;   -- can run migrations (DDL)
ALTER ROLE db_datareader ADD MEMBER passes_user;
ALTER ROLE db_datawriter ADD MEMBER passes_user;
GO

USE analytics;
GO
IF USER_ID('analytics_user') IS NULL CREATE USER analytics_user FOR LOGIN analytics_user;
ALTER ROLE db_ddladmin  ADD MEMBER analytics_user;
ALTER ROLE db_datareader ADD MEMBER analytics_user;
ALTER ROLE db_datawriter ADD MEMBER analytics_user;
GO
