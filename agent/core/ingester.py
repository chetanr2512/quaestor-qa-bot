from typing import List
from ..models import Ticket
from ..integrations import SupabaseClient, SheetsClient, DocsClient, JiraClient

class TicketIngester:
    def __init__(self):
        self.supabase = SupabaseClient()
        self.sheets = SheetsClient()
        self.docs = DocsClient()
        self.jira = JiraClient()

    def fetch_from_jira(self, jql: str) -> List[Ticket]:
        print(f"Fetching tickets from Jira with JQL: {jql}")
        tickets = self.jira.search_tickets(jql)
        self._save_to_db(tickets)
        return tickets

    def fetch_from_sheets(self, spreadsheet_id: str, sheet_name: str) -> List[Ticket]:
        print(f"Fetching tickets from Sheets (ID: {spreadsheet_id}, Sheet: {sheet_name})")
        tickets = self.sheets.get_tickets_from_sheet(spreadsheet_id, sheet_name)
        self._save_to_db(tickets)
        return tickets

    def fetch_from_docs(self, document_id: str) -> List[Ticket]:
        print(f"Fetching tickets from Docs (ID: {document_id})")
        text = self.docs.get_document_text(document_id)
        tickets = self.docs.parse_tickets_from_text(text, document_id)
        self._save_to_db(tickets)
        return tickets

    def _save_to_db(self, tickets: List[Ticket]):
        """Persist ingested tickets to Supabase"""
        for t in tickets:
            try:
                self.supabase.insert_ticket(t)
            except Exception as e:
                print(f"Error saving ticket {t.id} to Supabase: {e}")
