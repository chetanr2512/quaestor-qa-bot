import os
import gspread
from google.oauth2.service_account import Credentials
from ..models import Ticket

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class SheetsClient:
    def __init__(self, credentials_path: str = None):
        if not credentials_path:
            credentials_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'credentials.json'))
        self.credentials_path = credentials_path
        self.client = None
        self._authenticate()

    def _authenticate(self):
        token_path = os.path.join(os.path.dirname(self.credentials_path), 'token_sheets.json')
        creds = None
        
        # The file token_sheets.json stores the user's access and refresh tokens
        if os.path.exists(token_path):
            from google.oauth2.credentials import Credentials as OAuthCredentials
            creds = OAuthCredentials.from_authorized_user_file(token_path, SCOPES)
            
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            from google.auth.transport.requests import Request
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                from google_auth_oauthlib.flow import InstalledAppFlow
                
                # Check if using .env variables instead of a JSON file
                client_id = os.getenv("GOOGLE_CLIENT_ID")
                client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
                
                if client_id and client_secret:
                    client_config = {
                        "installed": {
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": ["http://localhost:8080/"]
                        }
                    }
                    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                else:
                    if not os.path.exists(self.credentials_path):
                        print(f"Error: OAuth client_secret file not found at {self.credentials_path} and GOOGLE_CLIENT_ID not found in .env")
                        return
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                    
                creds = flow.run_local_server(
                    port=8080,
                    access_type='offline',
                    prompt='consent',
                )
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
                
        try:
            self.client = gspread.authorize(creds)
        except Exception as e:
            print(f"Error authenticating with Google Sheets: {e}")

    def get_tickets_from_sheet(self, spreadsheet_id: str, sheet_name: str = 'Tickets') -> list[Ticket]:
        """Fetch tickets from a specific sheet"""
        if not self.client:
            print("Not authenticated. Returning empty tickets.")
            return []
            
        try:
            doc = self.client.open_by_key(spreadsheet_id)
            try:
                sheet = doc.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                # Fallback to the very first sheet if "Tickets" tab isn't found
                sheet = doc.sheet1
                print(f"Tab '{sheet_name}' not found, falling back to first tab.")
                
            records = sheet.get_all_records()
            
            tickets = []
            import uuid
            for row in records:
                # Convert all keys to lowercase for case-insensitive matching
                row_lower = {k.lower(): v for k, v in row.items()}
                
                # Skip empty rows where title is blank
                title = row_lower.get('title', '')
                if not title:
                    continue
                    
                tickets.append(Ticket(
                    id=str(uuid.uuid4()),
                    title=title,
                    description=row_lower.get('description', ''),
                    source='sheets',
                    source_id=str(row_lower.get('id', '')),
                    status=row_lower.get('status', 'open')
                ))
            return tickets
        except gspread.exceptions.APIError as e:
            print(f"Google API Error (Did you share the sheet with the service account?): {e}")
            return []
        except Exception as e:
            print(f"Error fetching tickets from sheet: {e}")
            return []

    def write_results_to_sheet(self, spreadsheet_id: str, results: list[dict], sheet_name: str = 'Results'):
        """Write test results back to a Google Sheet"""
        if not self.client: return
        
        try:
            doc = self.client.open_by_key(spreadsheet_id)
            try:
                sheet = doc.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                sheet = doc.add_worksheet(title=sheet_name, rows=100, cols=10)
                # Add headers
                sheet.append_row(["Test Case ID", "Name", "Status", "Duration", "Error"])
                
            rows = []
            for r in results:
                rows.append([
                    r.get('test_case_id', ''),
                    r.get('name', ''),
                    r.get('status', ''),
                    r.get('duration_seconds', 0),
                    r.get('error_message', '')
                ])
                
            if rows:
                sheet.append_rows(rows)
        except Exception as e:
            print(f"Error writing to sheet: {e}")

    def write_requirements_test_cases_to_sheet(self, spreadsheet_id: str, test_cases: list, metadata: dict = None, sheet_name: str = 'Requirements TCs'):
        """Write RFC/PRD-generated test cases to a Google Sheet in TestRail format."""
        if not self.client: return

        try:
            doc = self.client.open_by_key(spreadsheet_id)
            try:
                sheet = doc.worksheet(sheet_name)
                sheet.clear()
            except Exception:
                sheet = doc.add_worksheet(title=sheet_name, rows=500, cols=12)

            headers = [
                "ID", "RFC Section", "Title", "Type", "Priority",
                "Preconditions", "Steps", "Expected Result", "Test Data"
            ]
            sheet.append_row(headers)

            rows = []
            for i, tc in enumerate(test_cases, 1):
                rows.append([
                    f"TC-{i:04d}",
                    tc.rfc_section or "",
                    tc.name,
                    tc.test_category or tc.type,
                    tc.priority.title(),
                    tc.preconditions or "",
                    " | ".join(tc.steps),
                    tc.expected_result or (tc.assertions[0] if tc.assertions else ""),
                    "; ".join(f"{k}={v}" for k, v in tc.test_data.items()),
                ])
            if rows:
                sheet.append_rows(rows)

            if metadata:
                sheet.append_row([])
                sheet.append_row(["Coverage Gaps / Clarifications Needed"])
                for gap in metadata.get("coverage_gaps", []):
                    sheet.append_row([gap])

                sheet.append_row([])
                sheet.append_row(["Top 20 Regression Tests"])
                for t in metadata.get("regression_tests", []):
                    sheet.append_row([t])

                sheet.append_row([])
                sheet.append_row(["Top 10 Automation Candidates"])
                for t in metadata.get("automation_candidates", []):
                    sheet.append_row([t])

            print(f"RFC test cases written to sheet '{sheet_name}'.")
        except Exception as e:
            print(f"Error writing RFC test cases to sheet: {e}")

    def write_test_cases_to_sheet(self, spreadsheet_id: str, test_cases: list, sheet_name: str = 'Test Cases'):
        """Write generated test cases to a Google Sheet"""
        if not self.client: return
        
        try:
            doc = self.client.open_by_key(spreadsheet_id)
            try:
                sheet = doc.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                sheet = doc.add_worksheet(title=sheet_name, rows=100, cols=10)
                # Add headers
                sheet.append_row(["Test Case ID", "Ticket ID", "Name", "Type", "Priority", "Steps", "Assertions"])
                
            rows = []
            for tc in test_cases:
                rows.append([
                    tc.id,
                    tc.ticket_id,
                    tc.name,
                    tc.type,
                    tc.priority,
                    " | ".join(tc.steps),
                    " | ".join(tc.assertions)
                ])
                
            if rows:
                sheet.append_rows(rows)
        except Exception as e:
            print(f"Error writing test cases to sheet: {e}")

    def get_spreadsheet_as_text(self, spreadsheet_id: str) -> str:
        """Fetch all sheets in the spreadsheet and format them as CSV-like text for the LLM."""
        out = ""
        # Google Sheets logic
        if not self.client:
            print("Not authenticated. Cannot fetch spreadsheet.")
            return ""
            
        try:
            doc = self.client.open_by_key(spreadsheet_id)
            for sheet in doc.worksheets():
                out += f"\n\n--- SHEET: {sheet.title} ---\n"
                records = sheet.get_all_values()
                for row in records:
                    out += ",".join([f'"{str(cell).replace(chr(34), chr(34)+chr(34))}"' if ',' in str(cell) or '\n' in str(cell) else str(cell) for cell in row]) + "\n"
            return out
        except gspread.exceptions.APIError as e:
            print(f"Google API Error (Did you share the sheet with the service account?): {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Details: {e.response.text}")
            return ""
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"Error: Spreadsheet with ID '{spreadsheet_id}' not found. Please verify the ID and ensure it is shared with the service account.")
            return ""
        except Exception as e:
            import traceback
            print(f"Error fetching spreadsheet: {e}")
            traceback.print_exc()
            return ""

    def update_testplan_statuses(self, spreadsheet_id: str, statuses: dict):
        """Batch update statuses for multiple test IDs"""
        if not self.client or not statuses: return
        try:
            doc = self.client.open_by_key(spreadsheet_id)
            for sheet in doc.worksheets():
                records = sheet.get_all_values()
                
                # Find Status column index
                status_col_idx = -1
                for row_idx, row in enumerate(records):
                    for col_idx, cell in enumerate(row):
                        if str(cell).strip().lower() == 'status':
                            status_col_idx = col_idx
                            break
                    if status_col_idx != -1:
                        break
                        
                if status_col_idx == -1:
                    continue # No Status column found in this sheet
                    
                updates = []
                for row_idx, row in enumerate(records):
                    for cell in row:
                        val = str(cell).strip()
                        if val in statuses:
                            # We found a Test ID in this row!
                            # gspread is 1-indexed for rows and cols
                            updates.append({
                                'range': gspread.utils.rowcol_to_a1(row_idx + 1, status_col_idx + 1),
                                'values': [[statuses[val]]]
                            })
                            break # Only one test_id per row
                            
                if updates:
                    sheet.batch_update(updates)
                    print(f"Batch updated {len(updates)} statuses in sheet '{sheet.title}'")
                    
        except Exception as e:
            print(f"Error batch updating testplan statuses: {e}")
