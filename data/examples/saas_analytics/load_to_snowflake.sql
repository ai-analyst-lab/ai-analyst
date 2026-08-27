-- ============================================================
-- SaaS Analytics Sample Dataset — Snowflake Load Script
-- Run this after connecting via /setup-snowflake
-- ============================================================

-- 1. Create a dedicated database + schema
CREATE DATABASE IF NOT EXISTS SAAS_ANALYTICS;
USE DATABASE SAAS_ANALYTICS;
CREATE SCHEMA IF NOT EXISTS PUBLIC;
USE SCHEMA PUBLIC;

-- 2. Create tables
CREATE OR REPLACE TABLE users (
    user_id          VARCHAR(10)   PRIMARY KEY,
    signup_date      DATE,
    country          VARCHAR(5),
    plan             VARCHAR(20),
    age              INT,
    acquisition_channel VARCHAR(30),
    is_active        BOOLEAN
);

CREATE OR REPLACE TABLE events (
    event_id         VARCHAR(10)   PRIMARY KEY,
    user_id          VARCHAR(10)   REFERENCES users(user_id),
    event_type       VARCHAR(30),
    event_timestamp  TIMESTAMP_NTZ,
    platform         VARCHAR(10),
    session_id       VARCHAR(10)
);

CREATE OR REPLACE TABLE orders (
    order_id         VARCHAR(10)   PRIMARY KEY,
    user_id          VARCHAR(10)   REFERENCES users(user_id),
    order_date       DATE,
    amount           DECIMAL(10,2),
    plan             VARCHAR(20),
    status           VARCHAR(20),
    currency         VARCHAR(5)
);

-- 3. Create internal stage for CSV upload
CREATE OR REPLACE STAGE saas_stage
    FILE_FORMAT = (TYPE = 'CSV' FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1);

-- 4. After uploading CSVs to the stage via SnowSQL or Snowsight:
--    PUT file://path/to/users.csv @saas_stage;
--    PUT file://path/to/events.csv @saas_stage;
--    PUT file://path/to/orders.csv @saas_stage;

-- 5. Copy into tables
COPY INTO users   FROM @saas_stage/users.csv;
COPY INTO events  FROM @saas_stage/events.csv;
COPY INTO orders  FROM @saas_stage/orders.csv;

-- 6. Verify row counts
SELECT 'users'  AS tbl, COUNT(*) AS rows FROM users
UNION ALL
SELECT 'events', COUNT(*) FROM events
UNION ALL
SELECT 'orders', COUNT(*) FROM orders;
