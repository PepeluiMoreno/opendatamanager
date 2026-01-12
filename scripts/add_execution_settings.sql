-- Add execution settings fields to resource table

-- Add columns with defaults
ALTER TABLE opendata.resource
ADD COLUMN IF NOT EXISTS max_workers INTEGER DEFAULT 1;

ALTER TABLE opendata.resource
ADD COLUMN IF NOT EXISTS timeout_seconds INTEGER DEFAULT 300;

ALTER TABLE opendata.resource
ADD COLUMN IF NOT EXISTS retry_attempts INTEGER DEFAULT 0;

ALTER TABLE opendata.resource
ADD COLUMN IF NOT EXISTS retry_delay_seconds INTEGER DEFAULT 60;

ALTER TABLE opendata.resource
ADD COLUMN IF NOT EXISTS execution_priority INTEGER DEFAULT 0;

-- Update existing NULL values (if any)
UPDATE opendata.resource SET max_workers = 1 WHERE max_workers IS NULL;
UPDATE opendata.resource SET timeout_seconds = 300 WHERE timeout_seconds IS NULL;
UPDATE opendata.resource SET retry_attempts = 0 WHERE retry_attempts IS NULL;
UPDATE opendata.resource SET retry_delay_seconds = 60 WHERE retry_delay_seconds IS NULL;
UPDATE opendata.resource SET execution_priority = 0 WHERE execution_priority IS NULL;

-- Make columns NOT NULL
ALTER TABLE opendata.resource ALTER COLUMN max_workers SET NOT NULL;
ALTER TABLE opendata.resource ALTER COLUMN timeout_seconds SET NOT NULL;
ALTER TABLE opendata.resource ALTER COLUMN retry_attempts SET NOT NULL;
ALTER TABLE opendata.resource ALTER COLUMN retry_delay_seconds SET NOT NULL;
ALTER TABLE opendata.resource ALTER COLUMN execution_priority SET NOT NULL;

-- Update alembic version table
INSERT INTO opendata.alembic_version (version_num)
VALUES ('20260111_0100')
ON CONFLICT (version_num) DO NOTHING;

-- Display success message
SELECT 'Execution settings added successfully!' as message;
