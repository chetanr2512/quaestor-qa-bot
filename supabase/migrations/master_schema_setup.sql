-- Master Schema Setup for QA Agent
-- This script safely updates or creates the complete schema, including all custom columns and websocket setups.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Tickets Table
CREATE TABLE IF NOT EXISTS public.tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- Ensure the ticket source check is up to date (adds requirements and testplan)
ALTER TABLE public.tickets DROP CONSTRAINT IF EXISTS tickets_source_check;
ALTER TABLE public.tickets ADD CONSTRAINT tickets_source_check 
    CHECK (source IN ('jira', 'sheets', 'docs', 'manual', 'requirements', 'testplan'));

-- 2. Test Cases Table (Includes all new spreadsheet & requirements columns)
CREATE TABLE IF NOT EXISTS public.test_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES public.tickets(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    automation_status TEXT,
    preconditions TEXT,
    expected_result TEXT,
    rfc_section TEXT,
    test_category TEXT,
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    assertions JSONB NOT NULL DEFAULT '[]'::jsonb,
    test_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    ai_generated BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- Drop old rigid constraints to support dynamic mapping from spreadsheets
ALTER TABLE public.test_cases DROP CONSTRAINT IF EXISTS test_cases_type_check;
ALTER TABLE public.test_cases DROP CONSTRAINT IF EXISTS test_cases_priority_check;

-- Ensure columns exist if the table was already created before
ALTER TABLE public.test_cases
    ADD COLUMN IF NOT EXISTS automation_status TEXT,
    ADD COLUMN IF NOT EXISTS preconditions TEXT,
    ADD COLUMN IF NOT EXISTS expected_result TEXT,
    ADD COLUMN IF NOT EXISTS rfc_section TEXT,
    ADD COLUMN IF NOT EXISTS test_category TEXT;

-- 3. Test Runs Table
CREATE TABLE IF NOT EXISTS public.test_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    total_tests INTEGER NOT NULL DEFAULT 0,
    passed INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0,
    duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    api_cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now()),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 4. Test Results Table
CREATE TABLE IF NOT EXISTS public.test_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    test_case_id UUID NOT NULL REFERENCES public.test_cases(id) ON DELETE CASCADE,
    test_run_id UUID NOT NULL REFERENCES public.test_runs(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('pass', 'fail', 'skip', 'error')),
    screenshot_url TEXT,
    logs JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB,
    duration_seconds DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    error_message TEXT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc', now())
);

-- 5. Create Storage Bucket for Screenshots (Safely ignoring if it exists)
INSERT INTO storage.buckets (id, name, public) 
VALUES ('screenshots', 'screenshots', true)
ON CONFLICT (id) DO NOTHING;

-- 6. Row Level Security (RLS) Policies
ALTER TABLE public.tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Enable all operations for all users" ON public.tickets;
CREATE POLICY "Enable all operations for all users" ON public.tickets FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Enable all operations for all users" ON public.test_cases;
CREATE POLICY "Enable all operations for all users" ON public.test_cases FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Enable all operations for all users" ON public.test_runs;
CREATE POLICY "Enable all operations for all users" ON public.test_runs FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Enable all operations for all users" ON public.test_results;
CREATE POLICY "Enable all operations for all users" ON public.test_results FOR ALL USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "Public Access" ON storage.objects;
CREATE POLICY "Public Access" ON storage.objects FOR ALL USING (bucket_id = 'screenshots') WITH CHECK (bucket_id = 'screenshots');

-- 7. Indexes for Performance
CREATE INDEX IF NOT EXISTS idx_tickets_source_id ON public.tickets(source_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_ticket_id ON public.test_cases(ticket_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_rfc_section ON public.test_cases(rfc_section);
CREATE INDEX IF NOT EXISTS idx_test_results_run_id ON public.test_results(test_run_id);

-- 8. Enable Realtime (Websockets) for live dashboard updates
BEGIN;
  DROP PUBLICATION IF EXISTS supabase_realtime;
  CREATE PUBLICATION supabase_realtime FOR TABLE 
    public.tickets, 
    public.test_cases, 
    public.test_runs, 
    public.test_results;
COMMIT;

-- 9. Reload the schema cache for the API (Fixes PGRST204 errors instantly)
NOTIFY pgrst, 'reload schema';
