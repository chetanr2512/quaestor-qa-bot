import argparse
import asyncio
import os
from dotenv import load_dotenv

# Load env before importing anything that might use settings
load_dotenv()

from .core import TicketIngester, TestCaseGenerator, TestClassifier, TestExecutor, Reporter
from .models import Ticket


async def run_pipeline(source: str, source_id: str, sheets_id: str = None, csv_out: str = None, project_key: str = "QA", re_run: bool = False, crit: bool = False, high: bool = False, med: bool = False, low: bool = False, headless: bool = False, sheet_name: str = None):
    print(f"🚀 Starting QA Automation Agent Pipeline...")

    # ------------------------------------------------------------------
    # Requirements / PRD mode
    # Generate (or reuse) a full test suite from a requirements .md file.
    # ------------------------------------------------------------------
    if source == 'requirements':
        # Always use agent/requirements.md — fixed convention, no --source-id needed
        agent_dir = os.path.dirname(__file__)
        source_id = os.path.join(agent_dir, 'requirements.md')

        if not os.path.exists(source_id):
            print(f"Error: requirements file not found at agent/requirements.md")
            print("       Create agent/requirements.md and paste your PRD/RFC content into it.")
            return

        with open(source_id, 'r', encoding='utf-8') as f:
            req_content = f.read()

        if not req_content.strip():
            print("Error: requirements file is empty.")
            return

        req_name = os.path.basename(source_id)
        print(f"📄 Loaded requirements from: {source_id} ({len(req_content)} chars)")

        generator = TestCaseGenerator()
        test_cases, metadata = generator.generate_from_requirements(req_content, source_id=req_name)

        if test_cases:
            print(f"   Coverage gaps identified : {len(metadata.get('coverage_gaps', []))}")
            print(f"   Top regression tests     : {len(metadata.get('regression_tests', []))}")
            print(f"   Automation candidates    : {len(metadata.get('automation_candidates', []))}")

            allowed_severities = []
            if crit: allowed_severities.append('critical')
            if high: allowed_severities.append('high')
            if med: allowed_severities.append('medium')
            if low: allowed_severities.append('low')
            if not allowed_severities:
                allowed_severities = ['critical', 'high', 'medium', 'low']
                
            runnable_cases = [tc for tc in test_cases if tc.priority.lower() in allowed_severities]
            
            import json
            manifest_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'requirements_to_TCs', '.manifest.json'))
            manifest = {}
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                except Exception:
                    pass
            
            entry = manifest.get(req_name, {})
            results = []
            
            if not re_run and entry.get('last_run_id'):
                print(f"Skipping execution. Tests already executed in run {entry['last_run_id']}.")
                if entry.get('last_jira_ticket') and entry.get('subtasks_created'):
                    print(f"Already executed and the ticket also created: {entry['last_jira_ticket']}")
                    results = [] # clear results to skip ticket creation
                elif entry.get('last_jira_ticket') and not entry.get('subtasks_created'):
                    print(f"Main ticket {entry['last_jira_ticket']} exists, but subtasks failed. Fetching results to retry subtasks...")
                    from .integrations.supabase_client import SupabaseClient
                    supabase = SupabaseClient()
                    results = supabase.get_results_for_run(entry['last_run_id'])
                else:
                    print("Test executed but Jira ticket not created. Fetching previous results...")
                    from .integrations.supabase_client import SupabaseClient
                    supabase = SupabaseClient()
                    results = supabase.get_results_for_run(entry['last_run_id'])
            else:
                if len(allowed_severities) == 4:
                    print(f"Executing all {len(runnable_cases)} test cases automatically...")
                else:
                    severity_str = "/".join([s.title() for s in allowed_severities])
                    print(f"Executing {len(runnable_cases)} {severity_str} priority test cases automatically...")
                
                executor = TestExecutor(headless=headless)
                results = await executor.execute_all(runnable_cases)
                if results and hasattr(results[0], 'test_run_id'):
                    entry['last_run_id'] = results[0].test_run_id
                    # Reset Jira tracking for the new run
                    entry.pop('last_jira_ticket', None)
                    entry.pop('subtasks_created', None)
                    manifest[req_name] = entry
                    with open(manifest_path, 'w', encoding='utf-8') as f:
                        json.dump(manifest, f, indent=2)
            
            failed_results = [r for r in results if r.status == 'fail']
            if failed_results:
                from .integrations.jira_client import JiraClient
                jira_client = JiraClient()
                
                bug_key = entry.get('last_jira_ticket')
                if not bug_key:
                    print(f"Found {len(failed_results)} failed tests. Creating Jira Bug ticket in project {project_key}...")
                    import datetime
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    bug_key = jira_client.create_issue(
                        project_key=project_key,
                        summary=f"Test Run {timestamp}",
                        description=f"Automated test run generated from requirements found {len(failed_results)} failures.",
                        issuetype="Bug"
                    )
                    
                    if bug_key:
                        print(f"Created Jira Bug: {bug_key}. Adding subtasks...")
                        entry['last_jira_ticket'] = bug_key
                        manifest[req_name] = entry
                        with open(manifest_path, 'w', encoding='utf-8') as f:
                            json.dump(manifest, f, indent=2)

                if bug_key and not entry.get('subtasks_created'):
                    print(f"Creating subtasks under parent ticket {bug_key}...")
                    test_case_map = {tc.id: tc for tc in runnable_cases}
                    subtasks_success = True
                    for r in failed_results:
                        tc = test_case_map.get(r.test_case_id)
                        if tc:
                            steps_text = "\n".join([f"- {s}" for s in tc.steps]) if tc.steps else "No steps provided"
                            sub_key = jira_client.create_subtask(
                                project_key=project_key,
                                parent_key=bug_key,
                                summary=f"Failed Test: {tc.name[:200]}",
                                description=f"Error message: {r.error_message}\n\nSteps:\n{steps_text}"
                            )
                            if not sub_key:
                                subtasks_success = False
                                
                    if subtasks_success:
                        entry['subtasks_created'] = True
                        manifest[req_name] = entry
                        with open(manifest_path, 'w', encoding='utf-8') as f:
                            json.dump(manifest, f, indent=2)
                        print(f"✅ All subtasks attached to {bug_key} successfully.")
                    else:
                        print("⚠️ Some subtasks failed to create. Run again to retry.")

        if csv_out and test_cases:
            generator.export_to_csv(test_cases, csv_out, metadata)

        if sheets_id and test_cases:
            generator.export_requirements_suite_to_sheets(test_cases, metadata, sheets_id)

        print("✅ Requirements pipeline finished.")
        return

    # ------------------------------------------------------------------
    # Test Plan Extraction mode
    # ------------------------------------------------------------------
    if source == 'testplan':
        from .integrations.sheets_client import SheetsClient
        sheets_client = SheetsClient()
        spreadsheet_text = sheets_client.get_spreadsheet_as_text(source_id, sheet_name=sheet_name)
        if not spreadsheet_text:
            print("Error: Could not retrieve spreadsheet text.")
            return

        generator = TestCaseGenerator()
        all_test_cases = generator.generate_from_testplan(spreadsheet_text, source_id, re_run=re_run)
        
        if not all_test_cases:
            print("No test cases extracted.")
            return
            
        print(f"🧠 Extracted {len(all_test_cases)} test cases.")

        # We intentionally skip the TestClassifier here to preserve the exact 'type' 
        # (e.g. Smoke, Regression, Edge) extracted from the test plan spreadsheet.
        
        executor = TestExecutor(headless=headless)
        
        # Filter out manual test cases
        runnable_cases = [
            tc for tc in all_test_cases 
            if str(tc.automation_status).strip().lower() != 'manual'
        ]
        
        print(f"Skipped {len(all_test_cases) - len(runnable_cases)} manual test cases. Executing {len(runnable_cases)} automated tests...")
        
        # We ignore crit/high/med/low here for simplicity or apply custom logic if needed,
        # but the user said "they will be executed" so we just execute all runnable.
        results = await executor.execute_all(runnable_cases)
        
        reporter = Reporter()
        reporter.generate_report(results, test_cases=all_test_cases, tickets=[], sheets_id=sheets_id)
        
        # --- Update Original Spreadsheet Statuses ---
        statuses_to_update = {}
        tc_lookup = {tc.id: tc for tc in all_test_cases}
        
        # 1. Default to 'Blocked' for Manual tests
        for tc in all_test_cases:
            if tc.source_test_id:
                if tc.automation_status and tc.automation_status.lower() == 'manual':
                    statuses_to_update[tc.source_test_id] = 'Blocked'
                    
        # 2. Overwrite with actual test execution results
        for res in results:
            tc = tc_lookup.get(res.test_case_id)
            if tc and tc.source_test_id:
                # Convert 'pass' -> 'Pass', 'fail' -> 'Fail'
                statuses_to_update[tc.source_test_id] = res.status.capitalize()
                
        if statuses_to_update:
            print(f"📝 Updating {len(statuses_to_update)} statuses in the original Google Sheet...")
            from .integrations.sheets_client import SheetsClient
            sheets = SheetsClient()
            sheets.update_testplan_statuses(source_id, statuses_to_update)
            
        print("✅ Testplan pipeline finished.")
        return

    # ------------------------------------------------------------------
    # Ticket-based mode (existing flow)
    # ------------------------------------------------------------------

    # 1. Ingest Tickets
    ingester = TicketIngester()
    if source == 'jira':
        tickets = ingester.fetch_from_jira(source_id)
    elif source == 'sheets':
        tickets = ingester.fetch_from_sheets(source_id, "Tickets")
    elif source == 'docs':
        tickets = ingester.fetch_from_docs(source_id)
    else:
        import uuid
        tickets = [Ticket(
            id=str(uuid.uuid4()),
            title="Create Todo Item",
            description="As a user, I should be able to create a new todo item with high priority.",
            source="manual",
            source_id="TEST-1"
        )]
        ingester._save_to_db(tickets)
        print("Using mock ticket since no valid source was provided.")

    if not tickets:
        print("No tickets found. Exiting.")
        return

    print(f"📥 Ingested {len(tickets)} tickets.")

    # 2. Generate Test Cases
    generator = TestCaseGenerator()
    all_test_cases = []
    for t in tickets:
        cases = generator.generate_from_ticket(t)
        all_test_cases.extend(cases)

    print(f"🧠 Generated {len(all_test_cases)} test cases.")
    if sheets_id:
        generator.export_to_sheets(all_test_cases, sheets_id)

    # 3. Classify Tests
    classifier = TestClassifier()
    classifier.process_and_update(all_test_cases)

    frontend_count = sum(1 for tc in all_test_cases if tc.type == 'frontend')
    backend_count = sum(1 for tc in all_test_cases if tc.type == 'backend')
    print(f"🏷️ Classification complete: {frontend_count} frontend, {backend_count} backend.")

    # 4. Execute Tests
    executor = TestExecutor(headless=headless)
    
    # Apply severity filtering
    allowed_severities = []
    if crit: allowed_severities.append('critical')
    if high: allowed_severities.append('high')
    if med: allowed_severities.append('medium')
    if low: allowed_severities.append('low')
    
    if allowed_severities:
        runnable_cases = [tc for tc in all_test_cases if tc.priority.lower() in allowed_severities]
    else:
        runnable_cases = all_test_cases
        allowed_severities = ['critical', 'high', 'medium', 'low']
        
    if len(allowed_severities) == 4:
        print(f"Executing all {len(runnable_cases)} test cases automatically...")
    else:
        severity_str = "/".join([s.title() for s in allowed_severities])
        print(f"Executing {len(runnable_cases)} {severity_str} priority test cases automatically...")
        
    results = await executor.execute_all(runnable_cases)

    # 5. Export to CSV
    if csv_out and runnable_cases:
        generator.export_to_csv(runnable_cases, csv_out)

    # 6. Export to Sheets
    if sheets_id:
        generator.export_to_sheets(runnable_cases, sheets_id)

    # 5. Report Results
    reporter = Reporter()
    reporter.generate_report(results, test_cases=all_test_cases, tickets=tickets, sheets_id=sheets_id)

    print("✅ Pipeline execution finished.")


def main():
    parser = argparse.ArgumentParser(description="QA Automation Agent")
    parser.add_argument(
        "--source",
        type=str,
        choices=['jira', 'sheets', 'docs', 'mock', 'requirements', 'testplan'],
        default='mock',
        help="Source of tickets / requirements. Use 'testplan' for test plan spreadsheets.",
    )
    parser.add_argument(
        "--source-id",
        type=str,
        default="project=QA",
        help=(
            "JQL for Jira, or Google Document/Sheet ID. "
            "Not used in 'requirements' mode — the file is always agent/requirements.md."
        ),
    )
    parser.add_argument(
        "--sheets-id",
        type=str,
        help="Google Sheet ID to write results / test cases back to",
    )
    parser.add_argument(
        "--csv-out",
        type=str,
        default=None,
        help="(requirements mode) Path to write the generated test suite as a CSV file",
    )
    parser.add_argument("--project-key", type=str, default="QA", help="Jira Project Key for creating bugs (default: QA)")
    parser.add_argument("--sheet-name", type=str, default=None, help="Specific sheet/tab name to execute tests from (for testplan mode)")
    parser.add_argument("--re-run", action="store_true", help="Force re-execution of test cases regardless of cache")
    parser.add_argument("--crit", action="store_true", help="Run critical severity test cases")
    parser.add_argument("--high", action="store_true", help="Run high severity test cases")
    parser.add_argument("--med", action="store_true", help="Run medium severity test cases")
    parser.add_argument("--low", action="store_true", help="Run low severity test cases")
    parser.add_argument("--headless", action="store_true", help="Run browser tests in headless mode (no UI)")
    parser.add_argument("--claude", action="store_true", help="Force use of Anthropic Claude models")
    parser.add_argument("--gemini", action="store_true", help="Force use of Google Gemini models")

    args = parser.parse_args()
    
    from .config import settings
    if args.claude:
        settings.DEFAULT_LLM = "claude"
    elif args.gemini:
        settings.DEFAULT_LLM = "gemini"
        
    asyncio.run(run_pipeline(
        args.source, args.source_id, args.sheets_id, args.csv_out, 
        args.project_key, args.re_run, args.crit, args.high, args.med, args.low, args.headless, args.sheet_name
    ))

if __name__ == "__main__":
    main()
