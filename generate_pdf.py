"""
Generate Architecture Choices PDF for QA Automation Agent
"""
from fpdf import FPDF
import textwrap

class ChoicesPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, 'QA Automation Agent - Architecture Choices', 0, 1, 'R')
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')

    def section_title(self, title):
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(15, 23, 42)  # #0F172A
        self.ln(4)
        self.cell(0, 10, title, 0, 1)
        self.set_draw_color(34, 197, 94)  # #22C55E
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 80, self.get_y())
        self.set_line_width(0.2)
        self.ln(4)

    def sub_title(self, title):
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(30, 41, 59)
        self.ln(2)
        self.cell(0, 8, title, 0, 1)
        self.ln(1)

    def body_text(self, text):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(51, 65, 85)
        for line in text.split('\n'):
            wrapped = textwrap.wrap(line, width=95) or ['']
            for w in wrapped:
                self.cell(0, 5.5, w, 0, 1)

    def bullet(self, text, indent=10):
        self.set_font('Helvetica', '', 10)
        self.set_text_color(51, 65, 85)
        x = self.get_x()
        self.set_x(x + indent)
        self.set_font('Helvetica', 'B', 10)
        self.cell(5, 5.5, '-', 0, 0)  # bullet char
        self.set_font('Helvetica', '', 10)
        wrapped = textwrap.wrap(text, width=85)
        for i, w in enumerate(wrapped):
            if i > 0:
                self.set_x(x + indent + 5)
            self.cell(0, 5.5, w, 0, 1)

    def choice_block(self, chosen, alternative, reasons, comparison=None):
        # Chosen label
        self.set_fill_color(240, 253, 244)  # Light green bg
        self.set_draw_color(34, 197, 94)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(22, 163, 74)
        self.cell(90, 7, f'  CHOSEN: {chosen}', 1, 0, 'L', True)
        
        # Alternative label
        self.set_fill_color(254, 242, 242)  # Light red bg
        self.set_draw_color(239, 68, 68)
        self.set_text_color(220, 38, 38)
        self.cell(90, 7, f'  Alternative: {alternative}', 1, 1, 'L', True)
        self.ln(3)

        # Reasons
        self.set_text_color(51, 65, 85)
        for reason in reasons:
            self.bullet(reason)
        self.ln(2)

        # Comparison table if provided
        if comparison:
            self.set_font('Helvetica', 'B', 9)
            self.set_fill_color(241, 245, 249)
            self.set_text_color(30, 41, 59)
            self.set_draw_color(226, 232, 240)
            
            col_w = [60, 60, 60]
            headers = comparison[0]
            for i, h in enumerate(headers):
                self.cell(col_w[i], 6, h, 1, 0, 'C', True)
            self.ln()

            self.set_font('Helvetica', '', 9)
            self.set_text_color(71, 85, 105)
            for row in comparison[1:]:
                for i, cell in enumerate(row):
                    self.cell(col_w[i], 6, cell, 1, 0, 'L')
                self.ln()
            self.ln(3)


def generate_pdf():
    pdf = ChoicesPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ============ COVER PAGE ============
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font('Helvetica', 'B', 28)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 15, 'QA Automation Agent', 0, 1, 'C')
    
    pdf.set_font('Helvetica', '', 18)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 10, 'Architecture & Design Choices', 0, 1, 'C')
    
    pdf.ln(10)
    pdf.set_draw_color(34, 197, 94)
    pdf.set_line_width(1)
    pdf.line(70, pdf.get_y(), 140, pdf.get_y())
    pdf.set_line_width(0.2)
    
    pdf.ln(15)
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, 'Prepared for: Tri-POD QA Assignment', 0, 1, 'C')
    pdf.cell(0, 8, 'Author: Jitender', 0, 1, 'C')
    pdf.cell(0, 8, 'Date: June 2026', 0, 1, 'C')
    
    pdf.ln(30)
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 6, 'This document explains the rationale behind every major', 0, 1, 'C')
    pdf.cell(0, 6, 'technology and architecture decision in the QA Agent.', 0, 1, 'C')

    # ============ TABLE OF CONTENTS ============
    pdf.add_page()
    pdf.section_title('Table of Contents')
    toc_items = [
        '1. Executive Summary',
        '2. Browser Agent: Browser Use vs Stagehand',
        '3. Database: Supabase vs SQLite',
        '4. Backend: Cloudflare Workers vs FastAPI',
        '5. API Framework: Hono',
        '6. Dashboard: Next.js on Cloudflare Pages',
        '7. AI Model Strategy: Claude Sonnet + Haiku',
        '8. UI/UX Design System Choices',
        '9. Integration Architecture',
        '10. Cost Analysis & Budget',
    ]
    for item in toc_items:
        pdf.body_text(item)
        pdf.ln(1)

    # ============ EXECUTIVE SUMMARY ============
    pdf.add_page()
    pdf.section_title('1. Executive Summary')
    pdf.body_text(
        'This QA Automation Agent is designed to autonomously pull tickets from Jira, Google Docs, '
        'and Google Sheets, generate or fetch test cases using AI, classify them as frontend or '
        'backend tests, execute them against a target web application, and report results with '
        'screenshots and logs.'
    )
    pdf.ln(3)
    pdf.body_text('The architecture prioritizes three key principles:')
    pdf.ln(2)
    pdf.bullet('Zero infrastructure cost - Using free tiers of Cloudflare Workers, Supabase, and Cloudflare Pages')
    pdf.bullet('Autonomous intelligence - Browser Use agent with Claude AI for self-directed exploration')
    pdf.bullet('Easy deployment - One-command deploys, no Docker/VPS required')
    pdf.ln(3)
    
    pdf.sub_title('Technology Stack Overview')
    table = [
        ['Layer', 'Technology', 'Cost'],
        ['Agent Runtime', 'Python 3.12+ (local)', 'Free'],
        ['AI Model', 'Anthropic Claude Sonnet/Haiku', '$60 budget'],
        ['Browser Automation', 'Browser Use + Playwright', 'Free'],
        ['Backend API', 'Cloudflare Workers + Hono', 'Free (100K req/day)'],
        ['Database', 'Supabase PostgreSQL', 'Free (500MB)'],
        ['File Storage', 'Supabase Storage', 'Free (1GB)'],
        ['Dashboard', 'Next.js + Cloudflare Pages', 'Free'],
        ['Styling', 'Tailwind CSS + shadcn/ui', 'Free'],
    ]
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(248, 250, 252)
    for h in table[0]:
        pdf.cell(60, 7, h, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(51, 65, 85)
    pdf.set_fill_color(248, 250, 252)
    for i, row in enumerate(table[1:]):
        fill = i % 2 == 0
        for cell in row:
            pdf.cell(60, 6, cell, 1, 0, 'L', fill)
        pdf.ln()

    # ============ BROWSER AGENT ============
    pdf.add_page()
    pdf.section_title('2. Browser Agent: Browser Use vs Stagehand')
    pdf.body_text(
        'The assignment specifically mentions two open-source browser AI agents: Stagehand '
        '(browserbase/stagehand) and Browser Use (browser-use/browser-use). Both are LLM-driven '
        'browser automation frameworks built on Playwright.'
    )
    pdf.ln(4)

    pdf.choice_block(
        'Browser Use', 'Stagehand',
        [
            'Python-native: The entire agent core is Python. Browser Use integrates without any bridge layer, while Stagehand is TypeScript-first with a secondary Python wrapper.',
            'Autonomous reasoning loop: The assignment requires exploring an unfamiliar app "the way a QA hire would." Browser Use excels at autonomous exploration with its observe-plan-act loop, while Stagehand is better for known, deterministic workflows.',
            'Massive community: 97K+ GitHub stars vs ~3.4K for Stagehand. More examples, faster bug fixes, better documentation, and battle-tested in production.',
            'Built-in cost tracking: calculate_cost=True tracks token spend per run. Critical when operating under a $60 budget cap. Stagehand requires manual cost tracking.',
            'DOM-first approach: Browser Use reads DOM structure by default, saving 80-90% tokens compared to vision-only approaches. Only falls back to screenshots when needed.',
            'Zero cloud cost: Runs 100% locally with Playwright. Stagehand recommends Browserbase cloud ($20+/mo) for production use.',
            'Built-in retry handling: max_failures parameter provides step-level retry with automatic backoff, perfect for flaky UI tests.',
        ],
        [
            ['Feature', 'Browser Use', 'Stagehand'],
            ['Language', 'Python (native)', 'TypeScript (Python wrapper)'],
            ['GitHub Stars', '97,400+', '~3,400'],
            ['Autonomy', 'Full agent loop', 'Hybrid code+NL'],
            ['Cost Tracking', 'Built-in', 'Manual'],
            ['Retry Handling', 'max_failures param', 'Self-healing cache'],
            ['Cloud Required?', 'No', 'Recommended'],
            ['Claude Support', 'Native', 'Native'],
            ['Token Efficiency', 'DOM-first (80-90% savings)', 'CDP + caching'],
        ]
    )

    # ============ DATABASE ============
    pdf.add_page()
    pdf.section_title('3. Database: Supabase vs SQLite')
    pdf.body_text(
        'The agent needs to persist tickets, test cases, test results, and screenshots. '
        'Supabase provides a free PostgreSQL database with real-time subscriptions and file storage.'
    )
    pdf.ln(4)

    pdf.choice_block(
        'Supabase (PostgreSQL)', 'SQLite',
        [
            'Cloud-accessible: The dashboard (deployed on Cloudflare Pages) can query Supabase directly via its JavaScript client. SQLite is a local file that cannot be accessed from a web app without a server.',
            'Real-time subscriptions: Supabase Realtime enables live updates in the dashboard as tests execute. No need to build WebSocket infrastructure.',
            'File storage: Screenshots can be uploaded to Supabase Storage (1GB free) and served via CDN URLs. SQLite cannot store files.',
            'Shareable with evaluators: Just add their email to get access to the database. With SQLite, you would need to share the file manually.',
            'Free tier is generous: 500MB database, 1GB file storage, 50K monthly active users, unlimited API requests.',
            'Auto-generated REST API: Supabase creates REST endpoints for all tables automatically, reducing backend code.',
        ],
        [
            ['Feature', 'Supabase', 'SQLite'],
            ['Dashboard access', 'Direct via JS client', 'Needs server proxy'],
            ['Real-time updates', 'Built-in', 'Requires polling'],
            ['File storage', '1GB free', 'Local disk only'],
            ['Shareable', 'Add email', 'Share file'],
            ['Free tier', '500MB DB', 'Unlimited (local)'],
            ['Setup complexity', 'Create project (2 min)', 'Zero config'],
        ]
    )

    # ============ BACKEND ============
    pdf.add_page()
    pdf.section_title('4. Backend: Cloudflare Workers vs FastAPI')
    pdf.body_text(
        'The API layer serves as the bridge between the Python agent (running locally) and the '
        'Next.js dashboard (deployed globally). Cloudflare Workers provides a serverless edge '
        'runtime with zero cold starts.'
    )
    pdf.ln(4)

    pdf.choice_block(
        'Cloudflare Workers', 'FastAPI (Python)',
        [
            'Zero deployment cost: Free tier includes 100K requests/day, which is far more than this project needs. FastAPI would require a VPS ($5+/mo) or Docker container.',
            'One-command deploy: "wrangler deploy" pushes the API to 300+ edge locations globally. FastAPI needs Docker, a VPS, SSH, nginx, SSL certificates.',
            'Zero cold starts: Workers run on Cloudflare edge network with instant startup. FastAPI on a serverless platform would have 500ms-2s cold starts.',
            'Automatic HTTPS: SSL certificates are provisioned automatically. No manual cert management.',
            'Global CDN: API responses are served from the nearest edge location. FastAPI on a single VPS means latency from one region.',
            'The Python agent runs locally anyway: Since Browser Use requires a local browser, the agent must run on the developer machine. The API layer is thin (just CRUD on Supabase), so Workers is perfect.',
        ],
        [
            ['Feature', 'Cloudflare Workers', 'FastAPI'],
            ['Cost', 'Free (100K req/day)', '$5+/mo VPS'],
            ['Deploy', '1 command', 'Docker + VPS'],
            ['Cold starts', '0ms', '500ms-2s'],
            ['HTTPS', 'Automatic', 'Manual certs'],
            ['Global CDN', 'Yes (300+ locations)', 'Single region'],
            ['Scaling', 'Automatic', 'Manual'],
        ]
    )

    # ============ HONO ============
    pdf.add_page()
    pdf.section_title('5. API Framework: Hono')
    pdf.body_text(
        'Hono is a lightweight (14KB), ultrafast web framework designed specifically for '
        'Cloudflare Workers and edge runtimes.'
    )
    pdf.ln(3)
    pdf.sub_title('Why Hono?')
    pdf.bullet('Cloudflare-native: Built for Workers from the ground up. First-class support for env bindings, KV, D1, etc.')
    pdf.bullet('Express-like API: Familiar middleware pattern (app.get, app.post, app.use) minimizes learning curve.')
    pdf.bullet('14KB bundle: Tiny footprint keeps Workers within the free tier CPU limits (10ms).')
    pdf.bullet('Built-in middleware: CORS, auth, rate limiting, validation all included. No external deps needed.')
    pdf.bullet('TypeScript-first: Full type safety with excellent inference.')

    # ============ DASHBOARD ============
    pdf.ln(6)
    pdf.section_title('6. Dashboard: Next.js on Cloudflare Pages')
    pdf.body_text(
        'The dashboard provides real-time visibility into test execution, results, and agent activity.'
    )
    pdf.ln(3)
    pdf.bullet('Next.js 15: Latest version with React 19, server components, and app router.')
    pdf.bullet('Cloudflare Pages: Free hosting with automatic builds from Git. Global CDN, preview deployments.')
    pdf.bullet('Supabase Realtime: Dashboard subscribes to database changes for live updates. No WebSocket server needed.')
    pdf.bullet('Tailwind CSS + shadcn/ui: Pre-built, accessible components with dark mode support.')

    # ============ AI MODEL ============
    pdf.add_page()
    pdf.section_title('7. AI Model Strategy')
    pdf.body_text(
        'With a $60 Anthropic API budget, strategic model selection is critical. The agent uses '
        'different Claude models for different tasks based on complexity vs cost.'
    )
    pdf.ln(4)

    model_table = [
        ['Task', 'Model', 'Est. Cost/Call', 'Why'],
        ['Browser Agent', 'Claude Sonnet', '~$0.15', 'Complex DOM reasoning'],
        ['Test Generation', 'Claude Sonnet', '~$0.16', 'Structured output needed'],
        ['Classification', 'Claude Haiku', '~$0.02', 'Simple categorization'],
        ['Report Generation', 'Claude Haiku', '~$0.05', 'Template-based'],
        ['App Discovery', 'Claude Sonnet', '~$0.17', 'Understanding UI flows'],
    ]
    col_w = [40, 35, 30, 75]
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(248, 250, 252)
    for i, h in enumerate(model_table[0]):
        pdf.cell(col_w[i], 7, h, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(51, 65, 85)
    pdf.set_fill_color(248, 250, 252)
    for j, row in enumerate(model_table[1:]):
        fill = j % 2 == 0
        for i, cell in enumerate(row):
            pdf.cell(col_w[i], 6, cell, 1, 0, 'L', fill)
        pdf.ln()

    pdf.ln(4)
    pdf.sub_title('Budget Breakdown')
    budget_table = [
        ['Use Case', 'Est. Calls', 'Est. Cost'],
        ['Browser agent (frontend tests)', '~200', '$30'],
        ['Test case generation', '~50', '$8'],
        ['App discovery/exploration', '~30', '$5'],
        ['Test classification', '~100', '$2'],
        ['Report generation', '~20', '$1'],
        ['Development/debugging', '~50', '$8'],
        ['Buffer', '-', '$6'],
        ['TOTAL', '', '$54 (of $60)'],
    ]
    col_w2 = [70, 50, 60]
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(248, 250, 252)
    for i, h in enumerate(budget_table[0]):
        pdf.cell(col_w2[i], 7, h, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(51, 65, 85)
    for j, row in enumerate(budget_table[1:]):
        fill = j % 2 == 0
        bold = (j == len(budget_table) - 2)
        if bold:
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(240, 253, 244)
            fill = True
        for i, cell in enumerate(row):
            pdf.cell(col_w2[i], 6, cell, 1, 0, 'L', fill)
        pdf.ln()
        if bold:
            pdf.set_font('Helvetica', '', 9)
            pdf.set_fill_color(248, 250, 252)

    # ============ UI/UX ============
    pdf.add_page()
    pdf.section_title('8. UI/UX Design System Choices')
    pdf.body_text(
        'The design system was generated using the ui-ux-pro-max skill, which analyzed 161 color '
        'palettes, 86 UI styles, 57 font pairings, and 1,776 design specifications to recommend '
        'the optimal visual system for a QA testing dashboard.'
    )
    pdf.ln(3)

    pdf.sub_title('Product Type Match: Developer Tool / IDE')
    pdf.bullet('Primary style: Dark Mode (OLED) + Minimalism - Industry standard for developer tools')
    pdf.bullet('Dashboard pattern: Real-Time Monitor + Terminal aesthetic')
    pdf.bullet('Color theme: "Code dark + run green" - Deep slate backgrounds with green success indicators')
    pdf.bullet('Typography: Inter (UI) + JetBrains Mono (code/data) - The standard dev-tool pairing')
    
    pdf.ln(3)
    pdf.sub_title('Color Palette')
    colors = [
        ('Background', '#0F172A', 'Deep slate - reduces eye strain'),
        ('Card Surface', '#1B2336', 'Elevated elements'),
        ('Pass/Success', '#22C55E', 'Green - universal "go/pass"'),
        ('Fail/Error', '#EF4444', 'Red - universal "stop/fail"'),
        ('Warning', '#F59E0B', 'Amber - attention needed'),
        ('In Progress', '#3B82F6', 'Blue - active/running'),
        ('Text Primary', '#F8FAFC', 'High contrast on dark'),
        ('Text Secondary', '#94A3B8', 'Muted for labels'),
    ]
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(248, 250, 252)
    pdf.cell(45, 7, 'Token', 1, 0, 'C', True)
    pdf.cell(30, 7, 'Value', 1, 0, 'C', True)
    pdf.cell(105, 7, 'Purpose', 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(51, 65, 85)
    pdf.set_fill_color(248, 250, 252)
    for i, (name, val, purpose) in enumerate(colors):
        fill = i % 2 == 0
        pdf.cell(45, 6, name, 1, 0, 'L', fill)
        pdf.cell(30, 6, val, 1, 0, 'L', fill)
        pdf.cell(105, 6, purpose, 1, 0, 'L', fill)
        pdf.ln()

    pdf.ln(3)
    pdf.sub_title('Key UX Rules Applied')
    pdf.bullet('WCAG AA contrast: 4.5:1 minimum (7:1+ for dark mode text)')
    pdf.bullet('No emoji as structural icons - using Lucide SVG icons')
    pdf.bullet('44x44px minimum touch/click targets')
    pdf.bullet('150-300ms animation timing with prefers-reduced-motion support')
    pdf.bullet('4pt/8dp spacing system throughout')
    pdf.bullet('Virtualized lists for 50+ test cases')
    pdf.bullet('Never pure #000000 backgrounds (OLED smear prevention)')

    # ============ INTEGRATIONS ============
    pdf.add_page()
    pdf.section_title('9. Integration Architecture')
    pdf.body_text(
        'The agent integrates with four external services. Here is why each integration was designed the way it is.'
    )
    pdf.ln(3)

    pdf.sub_title('Jira REST API v3')
    pdf.bullet('Authentication: Basic Auth with API token (simplest, sufficient for a demo)')
    pdf.bullet('JQL queries for flexible ticket filtering by project, status, label')
    pdf.bullet('Results posted as comments on tickets for traceability')

    pdf.ln(2)
    pdf.sub_title('Google Sheets (gspread library)')
    pdf.bullet('Primary shareable output: Evaluators can directly open and inspect results')
    pdf.bullet('Color-coded pass/fail cells for visual scanning')
    pdf.bullet('Service Account auth (no OAuth popup needed)')

    pdf.ln(2)
    pdf.sub_title('Google Docs')
    pdf.bullet('Detailed narrative reports with embedded screenshots')
    pdf.bullet('Used for ticket descriptions and rich test documentation')

    pdf.ln(2)
    pdf.sub_title('Supabase Realtime')
    pdf.bullet('Dashboard subscribes to INSERT events on test_results table')
    pdf.bullet('Live KPI updates as tests complete - no polling or WebSocket server needed')
    pdf.bullet('Screenshot URLs served from Supabase Storage CDN')

    # ============ COST ANALYSIS ============
    pdf.ln(6)
    pdf.section_title('10. Cost Analysis')
    pdf.sub_title('Total Infrastructure Cost: $0/month')
    pdf.ln(2)
    
    cost_table = [
        ['Service', 'Free Tier Limit', 'Our Usage (Est.)'],
        ['Cloudflare Workers', '100K req/day', '~500 req/day'],
        ['Cloudflare Pages', 'Unlimited sites', '1 site'],
        ['Supabase DB', '500MB', '~50MB'],
        ['Supabase Storage', '1GB', '~200MB screenshots'],
        ['Supabase Auth', '50K MAU', 'Not used (API key)'],
        ['Google Sheets API', '300 req/min', '~50 req/run'],
        ['Google Docs API', '300 req/min', '~10 req/run'],
    ]
    col_w3 = [60, 60, 60]
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(248, 250, 252)
    for i, h in enumerate(cost_table[0]):
        pdf.cell(col_w3[i], 7, h, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(51, 65, 85)
    pdf.set_fill_color(248, 250, 252)
    for j, row in enumerate(cost_table[1:]):
        fill = j % 2 == 0
        for i, cell in enumerate(row):
            pdf.cell(col_w3[i], 6, cell, 1, 0, 'L', fill)
        pdf.ln()

    pdf.ln(4)
    pdf.body_text(
        'The only cost is the $60 Anthropic API credits provided for the assignment. '
        'All infrastructure services operate within their generous free tiers.'
    )

    # Save
    output_path = r'D:\coding ai  agent\QA testing agent\architecture-choices.pdf'
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")

if __name__ == '__main__':
    generate_pdf()
