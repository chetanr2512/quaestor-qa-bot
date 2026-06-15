import requests
from requests.auth import HTTPBasicAuth
from ..config import settings
from ..models import Ticket

class JiraClient:
    def __init__(self):
        self.url = settings.JIRA_URL.rstrip('/')
        self.email = settings.JIRA_EMAIL
        self.api_token = settings.JIRA_API_TOKEN
        self.auth = HTTPBasicAuth(self.email, self.api_token) if self.email and self.api_token else None

    def search_tickets(self, jql: str = "project = QA AND status = 'To Do'") -> list[Ticket]:
        """Fetch tickets using JQL"""
        if not self.auth or not self.url:
            print("Warning: Jira credentials missing")
            return []
            
        endpoint = f"{self.url}/rest/api/3/search/jql"
        headers = {"Accept": "application/json"}
        params = {
            "jql": jql, 
            "maxResults": 50,
            "fields": "summary,description,status"  # Explicitly request required fields
        }
        
        try:
            response = requests.get(endpoint, headers=headers, auth=self.auth, params=params)
            response.raise_for_status()
            data = response.json()
            
            tickets = []
            import uuid
            for issue in data.get('issues', []):
                # API v3 returns ADF or plain strings depending on configuration
                desc_text = "No description"
                desc_obj = issue.get('fields', {}).get('description')
                if desc_obj and isinstance(desc_obj, dict) and 'content' in desc_obj:
                    try:
                        desc_text = desc_obj['content'][0]['content'][0]['text']
                    except Exception:
                        pass
                elif isinstance(desc_obj, str):
                    desc_text = desc_obj

                tickets.append(Ticket(
                    id=str(uuid.uuid4()),
                    title=issue.get('fields', {}).get('summary', 'Untitled'),
                    description=desc_text,
                    source='jira',
                    source_id=str(issue.get('key') or f"JIRA-{uuid.uuid4().hex[:6]}"),
                    status=issue.get('fields', {}).get('status', {}).get('name', 'open')
                ))
            return tickets
        except Exception as e:
            print(f"Error fetching from Jira: {e}")
            return []

    def post_comment(self, issue_key: str, comment_text: str):
        """Post a comment with test results back to Jira"""
        if not self.auth or not self.url: return
        
        endpoint = f"{self.url}/rest/api/3/issue/{issue_key}/comment"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Atlassian Document Format for comments
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"text": comment_text, "type": "text"}
                        ]
                    }
                ]
            }
        }
        
        try:
            response = requests.post(endpoint, json=payload, headers=headers, auth=self.auth)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error posting comment to Jira: {e}")
            return False

    def _build_adf_from_text(self, text: str) -> dict:
        paragraphs = []
        for line in text.split('\n'):
            if line.strip():
                paragraphs.append({
                    "type": "paragraph",
                    "content": [{"text": line, "type": "text"}]
                })
            else:
                paragraphs.append({"type": "paragraph", "content": []})
        return {
            "type": "doc",
            "version": 1,
            "content": paragraphs
        }

    def create_issue(self, project_key: str, summary: str, description: str, issuetype: str = "Bug") -> str:
        if not self.auth or not self.url: return None
        endpoint = f"{self.url}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": self._build_adf_from_text(description),
                "issuetype": {"name": issuetype}
            }
        }
        try:
            response = requests.post(endpoint, json=payload, headers={"Accept": "application/json"}, auth=self.auth)
            response.raise_for_status()
            return response.json().get('key')
        except requests.exceptions.HTTPError as e:
            print(f"Error creating Jira issue. API Response: {e.response.text}")
            return None
        except Exception as e:
            print(f"Error creating Jira issue: {e}")
            return None

    def create_subtask(self, project_key: str, parent_key: str, summary: str, description: str) -> str:
        if not self.auth or not self.url: return None
        endpoint = f"{self.url}/rest/api/3/issue"
        payload = {
            "fields": {
                "project": {"key": project_key},
                "parent": {"key": parent_key},
                "summary": summary,
                "description": self._build_adf_from_text(description),
                "issuetype": {"name": "Sub-task"} # Or "Subtask"
            }
        }
        try:
            response = requests.post(endpoint, json=payload, headers={"Accept": "application/json"}, auth=self.auth)
            response.raise_for_status()
            return response.json().get('key')
        except requests.exceptions.HTTPError as e:
            # Fallback for Jira instances that use 'Subtask' instead of 'Sub-task'
            if "issuetype" in e.response.text and payload["fields"]["issuetype"]["name"] == "Sub-task":
                payload["fields"]["issuetype"]["name"] = "Subtask"
                try:
                    response2 = requests.post(endpoint, json=payload, headers={"Accept": "application/json"}, auth=self.auth)
                    response2.raise_for_status()
                    return response2.json().get('key')
                except requests.exceptions.HTTPError as e2:
                    print(f"Error creating Jira subtask (Subtask fallback). API Response: {e2.response.text}")
                    return None
                    
            print(f"Error creating Jira subtask. API Response: {e.response.text}")
            return None
        except Exception as e:
            print(f"Error creating Jira subtask: {e}")
            return None
