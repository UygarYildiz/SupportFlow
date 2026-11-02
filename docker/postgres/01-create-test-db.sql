-- Runs once when the Postgres volume is first created.
-- A separate database for automated tests so they never touch development data.
CREATE DATABASE supportflow_test OWNER supportflow;
