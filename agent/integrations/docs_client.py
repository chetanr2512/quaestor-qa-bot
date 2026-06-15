import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from ..models import Ticket

SCOPES = ['https://www.googleapis.com/auth/documents.readonly']

class DocsClient:
    def __init__(self, credentials_path: str = None):
        if not credentials_path:
            credentials_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'credentials.json'))
        
        self.credentials_path = credentials_path
        self.service = None
        self._authenticate()

    def _authenticate(self):
        token_path = os.path.join(os.path.dirname(self.credentials_path), 'token_docs.json')
        creds = None
        
        # The file token_docs.json stores the user's access and refresh tokens
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
            self.service = build('docs', 'v1', credentials=creds)
        except Exception as e:
            print(f"Error authenticating with Google Docs: {e}")

    def get_document_text(self, document_id: str) -> str:
        """Extract all text from a Google Doc"""
        if not self.service:
            print("Not authenticated. Returning empty string.")
            return ""
            
        try:
            doc = self.service.documents().get(documentId=document_id).execute()
            text = ""
            for element in doc.get('body').get('content'):
                if 'paragraph' in element:
                    for p_elem in element.get('paragraph').get('elements'):
                        if 'textRun' in p_elem:
                            text += p_elem.get('textRun').get('content')
            return text
        except Exception as e:
            print(f"Error reading Google Doc: {e}")
            return ""

    def parse_tickets_from_text(self, text: str, document_id: str) -> list[Ticket]:
        """Simple parser to extract tickets from formatted text. 
        In reality, this would likely use an LLM or regex to parse structured docs."""
        # This is a placeholder for actual parsing logic
        import uuid
        tickets = []
        if text.strip():
            tickets.append(Ticket(
                id=str(uuid.uuid4()),
                title=f"Doc Import - {document_id[:8]}",
                description=text[:500] + "..." if len(text) > 500 else text,
                source='docs',
                source_id=document_id
            ))
        return tickets
