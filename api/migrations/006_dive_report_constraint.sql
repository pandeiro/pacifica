-- 006_dive_report_constraint.sql
-- Add dive_report condition type for unstructured dive condition reports

DO $$
BEGIN
    -- Drop and recreate the conditions_type_valid constraint to include dive_report
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'conditions_type_valid'
    ) THEN
        ALTER TABLE conditions
            DROP CONSTRAINT conditions_type_valid;
    END IF;
    
    ALTER TABLE conditions
        ADD CONSTRAINT conditions_type_valid
        CHECK (condition_type IN (
            'visibility', 'water_temp', 'air_temp',
            'swell_height', 'swell_period', 'wind_speed', 'wind_direction',
            'dive_report'
        ));
END $$;
