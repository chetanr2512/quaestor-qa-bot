import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { createClient } from '@supabase/supabase-js'

type Bindings = {
  SUPABASE_URL: string
  SUPABASE_SECRET_KEY: string
}

const app = new Hono<{ Bindings: Bindings }>()

// Middleware
app.use('*', cors())

// Basic health check
app.get('/health', (c) => c.json({ status: 'ok', service: 'qa-agent-api' }))

// Fetch tickets
app.get('/api/tickets', async (c) => {
  const supabase = createClient(c.env.SUPABASE_URL, c.env.SUPABASE_SECRET_KEY)
  const { data, error } = await supabase
    .from('tickets')
    .select('*')
    .order('created_at', { ascending: false })
    
  if (error) return c.json({ error: error.message }, 500)
  return c.json(data)
})

// Fetch all test runs with their results
app.get('/api/runs', async (c) => {
  const supabase = createClient(c.env.SUPABASE_URL, c.env.SUPABASE_SECRET_KEY)
  const { data, error } = await supabase
    .from('test_runs')
    .select('*, test_results(*)')
    .order('started_at', { ascending: false })
    .limit(50)
    
  if (error) return c.json({ error: error.message }, 500)
  return c.json(data)
})

// Fetch a specific test run by ID
app.get('/api/runs/:id', async (c) => {
  const id = c.req.param('id')
  const supabase = createClient(c.env.SUPABASE_URL, c.env.SUPABASE_SECRET_KEY)
  const { data, error } = await supabase
    .from('test_runs')
    .select('*, test_results(*, test_cases(*))')
    .eq('id', id)
    .single()
    
  if (error) return c.json({ error: error.message }, 500)
  return c.json(data)
})

// Fetch test cases
app.get('/api/test-cases', async (c) => {
  const ticketId = c.req.query('ticket_id')
  const supabase = createClient(c.env.SUPABASE_URL, c.env.SUPABASE_SECRET_KEY)
  
  let query = supabase.from('test_cases').select('*')
  if (ticketId) {
    query = query.eq('ticket_id', ticketId)
  }
  
  const { data, error } = await query.order('created_at', { ascending: false })
  if (error) return c.json({ error: error.message }, 500)
  return c.json(data)
})

export default app
