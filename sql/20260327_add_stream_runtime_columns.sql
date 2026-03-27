-- Stream runtime columns for admin runtime/uptime visibility.
-- Safe to run multiple times on MySQL 8+ (uses IF NOT EXISTS).

ALTER TABLE streams
  ADD COLUMN IF NOT EXISTS stream_status TINYINT NOT NULL DEFAULT 0 AFTER current_source,
  ADD COLUMN IF NOT EXISTS stream_pid INT NULL AFTER stream_status,
  ADD COLUMN IF NOT EXISTS stream_started_at DATETIME NULL AFTER stream_pid;

-- Optional index to speed up runtime filtering/reporting.
CREATE INDEX ix_streams_stream_status ON streams (stream_status);
