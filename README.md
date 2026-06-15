# Autonomous QA Agent 🤖

An intelligent, end-to-end Autonomous QA testing pipeline driven by Claude 3.5 Sonnet and Google Gemini. 

This agent automatically reads human-written requirements from Jira or Google Sheets, generates structured test cases, visually navigates your frontend via Chromium using the `browser-use` engine, executes API backend tests, and finally reports the results to a real-time Next.js dashboard, Jira, and Google Sheets.

## 🌟 Features
- **Visual Browser Automation:** Uses Playwright + LLM Vision to physically click, type, and navigate through your frontend application like a real human.
- **AI Test Generation:** Converts messy Jira tickets or massive Test Plan spreadsheets into strict, step-by-step test cases with explicit assertions.
- **Multi-Model LLM Factory:** Intelligently routes generation and browser navigation through Anthropic (Claude) or Google (Gemini) with automatic failovers.
- **Real-Time Next.js Dashboard:** Built with Supabase WebSockets to stream live test execution status, pass/fail metrics, and logs straight to your browser.
- **Automated Reporting:** Automatically comments the final pass/fail test results back onto the original Jira ticket.

---

## 🚀 1. Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+
- A Supabase Project
- A Google Cloud Console account
- An Atlassian (Jira) account

### Python Setup
Before running the agent, you must install its dependencies and the Playwright browser binaries.

```bash
# 1. Create a virtual environment (optional but recommended)
python -m venv venv

# 2. Activate it 
# (Windows)
venv\Scripts\activate
# (Mac/Linux)
source venv/bin/activate

# 3. Install required Python packages
pip install -r agent/requirements.txt

# 4. Install Playwright Chromium browsers (Required!)
python -m playwright install
```

### Environment Variables

Because this architecture has three distinct pieces (the Python Agent, the Next.js Dashboard, and the Cloudflare Worker), you need to configure environment variables for each:

#### 1. Python Agent (`agent/.env`)
Create a `.env` file inside the `agent/` directory and populate it with the following keys:

```env
# LLM Providers (Multi-Model Support)
DEFAULT_LLM="claude" # Set to "claude" or "gemini" to change the default engine
ANTHROPIC_API_KEY="your-claude-api-key"
GOOGLE_API_KEY="your-gemini-api-key"

# Database (Supabase)
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SECRET_KEY="your-service-role-key"

# Application to Test
TARGET_APP_URL="https://qa-assignment-steel.vercel.app/"

# Jira Integration
JIRA_SERVER="https://your-workspace.atlassian.net"
JIRA_EMAIL="your-email@example.com"
JIRA_API_TOKEN="your-jira-api-token"

# Google OAuth 2.0 (For Google Sheets / Docs)
GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="your-client-secret"
```

#### 2. Next.js Dashboard (`dashboard/.env.local`)
To allow the frontend dashboard to connect to Supabase and stream real-time websocket updates, create a `.env.local` file inside the `dashboard/` directory:
```env
NEXT_PUBLIC_SUPABASE_URL="https://your-project.supabase.co"
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY="your-publishable-key"
```

#### 3. Cloudflare Worker (`worker/.dev.vars`)
If you are running the optional API Middle-Tier locally, create a `.dev.vars` file inside the `worker/` directory. This acts as your local secrets vault before pushing to Cloudflare:
```env
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SECRET_KEY="your-secret-key"
```

### Google OAuth Setup
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Google Sheets API** and **Google Docs API**.
3. Create new **OAuth 2.0 Client IDs** (Select "Desktop app" as the application type).
4. Add `http://localhost:8080/` to the "Authorized redirect URIs".
5. Paste the Client ID and Secret into your `.env` file. The first time you run the agent, it will open a browser to authenticate you.

### Supabase Database Setup
1. Open your Supabase Dashboard and navigate to the SQL Editor.
2. Run the `master_schema_setup.sql` file provided in `supabase/migrations/` to instantly provision all `tickets`, `test_cases`, `test_runs`, and `test_results` tables with the required constraints and WebSocket Realtime functionality enabled.

### Requirements Document Setup
To test an application using a local requirements file (PRD/RFC), you must create a file named `requirements.md` inside the `agent/` directory.
Paste your user stories, acceptance criteria, or product requirements directly into this file.

```bash
# Example: Create the file (then open it and paste your PRD inside)
touch agent/requirements.md
```
*Note: The agent tracks this file. If you run the command multiple times without modifying the text inside `requirements.md`, the AI generation is smartly skipped from the cache to save you time and money.*

### Handling Authenticated Applications (Google SSO / Login)
If your target application requires users to be logged in (e.g., via Google Authentication), you must manually extract your session cookies to bypass anti-bot protections. 

Run this built-in Playwright command from your root directory:
```bash
playwright codegen --save-storage=auth.json https://your-app.com/login
```
A browser will pop up. Log in manually. Once you close the browser, an `auth.json` file will be generated in your project root. The `BrowserRunner` engine will automatically detect this file and perfectly inject your live session into the AI bot every time it tests!

---

## 💻 2. Available Commands

### Running the Python QA Agent
Navigate to the root directory and run the agent using one of the following commands based on your source of truth:

**Generate and run tests from a Test Plan Spreadsheet (New Workflow):**
This massive-scale workflow connects to an existing QA Test Plan spreadsheet. It chunks the spreadsheet to avoid memory/rate limits, preserves existing manual UI tests, and seamlessly executes all `API` and `Playwright` automated tests while retaining the original test severities.
```bash
python -m agent.main --source testplan --source-id "YOUR_GOOGLE_SHEET_ID"
```

**Generate and run tests from a local Requirements file (Requirements Workflow):**
This workflow reads `agent/requirements.md`, generates test cases, automatically executes them against the live app, exports a CSV, and creates Jira Bug tickets for any failed tests.
```bash
python -m agent.main --source requirements --csv-out output/generated_test_suite.csv --project-key YOUR_PROJECT_KEY
```

**Advanced Command Line Flags:**
You can chain multiple flags together to deeply customize the agent's execution behavior:
- `--sheet-name <NAME>`: Restricts execution to a specific tab inside the Google Spreadsheet (e.g. `--sheet-name Hotlist`). Case-insensitive.
- `--claude`: Forces the engine to use Anthropic's Claude models for the current run, ignoring the `.env` default.
- `--gemini`: Forces the engine to use Google's Gemini models for the current run, ignoring the `.env` default.
- `--project-key <KEY>`: Specifies the Jira project to create Bug tickets and subtasks in (default is `QA`).
- `--re-run`: Bypasses the local `.manifest.json` caching mechanism and forces a complete re-execution of tests against the browser.
- `--headless`: Runs the chromium browser invisibly in the background to avoid rendering the UI on your screen. Drastically speeds up execution time!
- `--crit`, `--high`, `--med`, `--low`: Filter to execute only tests matching specific severities. (If no flags are passed, it defaults to executing *all* test cases).

**Example: Fast, invisible, Gemini-powered background test run:**
```bash
python -m agent.main --source testplan --source-id "SHEET_ID" --gemini --crit --high --headless
```

**Legacy Ticket-Based Workflows:**
Pull requirements from Jira:
```bash
python -m agent.main --source jira --source-id "project=YOUR_PROJECT_KEY AND status='In Progress'"
```

---

### Running the Real-Time Dashboard
The dashboard allows you to watch the agent execute tests in real-time and download CSV reports of historical runs.

```bash
cd dashboard
npm install
npm run dev
```
Access the dashboard at `http://localhost:3000`.

### Running the API Worker (Optional)
While the Next.js dashboard can connect directly to Supabase, the Cloudflare API Worker is designed to act as a secure middle-tier for production environments. It provides:
1. **Webhook Processing:** Acts as an always-on listener to catch inbound webhooks from Jira or GitHub to automatically trigger test runs.
2. **Security Proxy:** Safely handles third-party API keys (like Jira credentials) without exposing them to the frontend client.
3. **Edge Caching:** Reduces direct Supabase database reads to save costs at scale.

```bash
cd worker
npm install
npm run dev
```

---

## 🌍 3. Production Deployment (Fully Automated)

By default, this project runs manually via your terminal. To make it a fully automated, event-driven CI/CD pipeline, follow this production architecture:

### Step 1: Deploy the Webhook Listener (Cloudflare Worker)
Your worker needs a public URL to receive internet traffic from Jira.
1. Add a `POST /webhook/jira` route in `worker/src/index.ts` to listen for ticket status changes.
2. Deploy it to the edge:
```bash
cd worker
npx wrangler deploy
```

### Step 2: Configure Jira Webhooks
1. In Jira, go to **Project Settings > Webhooks > Create Webhook**.
2. Paste your new Cloudflare Worker URL (e.g., `https://qa-api.your-domain.workers.dev/webhook/jira`).
3. Set the trigger event to "Issue Updated" (specifically when moved to the "QA" column).

### Step 3: Dockerize the Python Agent (Job Queue)
You **cannot** run the Python agent inside the Cloudflare Worker because it requires a Chromium browser and Python binaries.
1. Create a `job_queue` table in Supabase.
2. When your Cloudflare Worker receives the Jira webhook, it inserts the Ticket ID into the `job_queue` table.
3. Package your `agent/` folder into a Docker container and host it on AWS Fargate, Google Cloud Run, or a standard VM.
4. Have the Docker container constantly listen to the Supabase `job_queue` table using Realtime WebSockets. When a job appears, it wakes up, runs the browser tests, updates the dashboard, and goes back to sleep.
