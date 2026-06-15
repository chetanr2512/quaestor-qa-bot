from typing import List
from ..models import TestResult
from ..integrations.sheets_client import SheetsClient
from ..integrations.jira_client import JiraClient

class Reporter:
    def __init__(self):
        self.sheets = SheetsClient()
        self.jira = JiraClient()
        
    def generate_report(self, results: List[TestResult], test_cases: list = None, tickets: list = None, sheets_id: str = None):
        """Compiles results and sends them to output destinations"""
        if not results:
            print("No results to report.")
            return
            
        passed = sum(1 for r in results if r.status == 'pass')
        failed = sum(1 for r in results if r.status == 'fail')
        total = len(results)
        
        print("\n" + "="*40)
        print("📊 TEST RUN SUMMARY")
        print("="*40)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print("="*40 + "\n")
        
        # Format results for Sheets
        if sheets_id:
            formatted_results = []
            for r in results:
                formatted_results.append({
                    "test_case_id": r.test_case_id,
                    "name": f"Test {r.test_case_id[:8]}", # We'd map name in real scenario
                    "status": r.status.upper(),
                    "duration_seconds": r.duration_seconds,
                    "error_message": r.error_message or ""
                })
            print("Writing results to Google Sheets...")
            self.sheets.write_results_to_sheet(sheets_id, formatted_results)
            
        # Post results to Jira
        if test_cases and tickets:
            jira_tickets = {t.id: t for t in tickets if t.source == 'jira' and t.source_id}
            if not jira_tickets:
                return
                
            # Group results by ticket
            ticket_results = {}
            test_case_map = {tc.id: tc for tc in test_cases}
            
            for r in results:
                tc = test_case_map.get(r.test_case_id)
                if not tc or tc.ticket_id not in jira_tickets:
                    continue
                ticket = jira_tickets[tc.ticket_id]
                if ticket.source_id not in ticket_results:
                    ticket_results[ticket.source_id] = {"passed": 0, "failed": 0, "details": []}
                    
                if r.status == 'pass':
                    ticket_results[ticket.source_id]["passed"] += 1
                else:
                    ticket_results[ticket.source_id]["failed"] += 1
                    
                ticket_results[ticket.source_id]["details"].append(
                    f"[{r.status.upper()}] {tc.name}" + (f" - Error: {r.error_message}" if r.status == 'fail' else "")
                )
                
            for jira_key, summary in ticket_results.items():
                print(f"Posting execution results to Jira ticket {jira_key}...")
                comment = (
                    f"🤖 *AI QA Agent Test Run Completed*\n\n"
                    f"✅ Passed: {summary['passed']}\n"
                    f"❌ Failed: {summary['failed']}\n\n"
                    f"*Details:*\n" + "\n".join(summary['details'])
                )
                self.jira.post_comment(jira_key, comment)
