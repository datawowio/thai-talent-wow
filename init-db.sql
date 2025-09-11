-- Initialize database for ML API testing
CREATE TABLE IF NOT EXISTS termination_results (
    id BIGSERIAL PRIMARY KEY,
    overall_summary JSONB,
    department_proportion JSONB,
    job_level_proportion JSONB,
    department_distribution JSONB,
    job_level_distribution JSONB,
    top_quitting_reason JSONB,
    reason_by_employee JSONB,
    reason_by_department JSONB,
    reason_by_job_level JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_termination_results_created_at ON termination_results(created_at);
CREATE INDEX IF NOT EXISTS idx_termination_results_overall_summary ON termination_results USING GIN(overall_summary);

-- Grant permissions to app_user
GRANT ALL PRIVILEGES ON TABLE termination_results TO app_user;
GRANT USAGE, SELECT ON SEQUENCE termination_results_id_seq TO app_user;