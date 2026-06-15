from typing import List
from ..models import TestCase
from ..integrations.llm_client import LLMClient
from ..integrations.supabase_client import SupabaseClient

class TestClassifier:
    def __init__(self):
        self.llm_client = LLMClient()
        self.supabase = SupabaseClient()
        
    def classify(self, test_case: TestCase) -> str:
        """Determines if a test case is frontend (UI) or backend (API)"""
        # First, try rule-based classification based on keywords in steps/assertions
        content_to_check = str(test_case.steps).lower() + str(test_case.assertions).lower()
        
        frontend_keywords = ['click', 'button', 'navigate', 'page', 'ui', 'render', 'visible', 'type', 'input', 'screen']
        backend_keywords = ['api', 'endpoint', 'status code', 'json', 'response', 'request', 'fetch', 'http', 'post', 'get']
        
        frontend_score = sum(1 for kw in frontend_keywords if kw in content_to_check)
        backend_score = sum(1 for kw in backend_keywords if kw in content_to_check)
        
        # Clear winner
        if frontend_score > backend_score + 1:
            return "frontend"
        elif backend_score > frontend_score + 1:
            return "backend"
            
        # Fallback to AI (Haiku for speed/cost)
        llm = self.llm_client.get_haiku()
        if not llm:
            # Default to frontend if we can't decide and have no LLM
            return "frontend"
            
        prompt = f"""
        Given the following test case steps and assertions, classify whether this is a 'frontend' test 
        (involving browser UI interactions) or a 'backend' test (involving direct API requests).
        
        Steps: {test_case.steps}
        Assertions: {test_case.assertions}
        
        Respond with exactly one word: either "frontend" or "backend".
        """
        
        try:
            response = llm.invoke(prompt)
            result = response.content.strip().lower()
            if "backend" in result:
                return "backend"
            return "frontend"
        except Exception:
            return "frontend"

    def process_and_update(self, test_cases: List[TestCase]):
        """Classify a list of test cases and update them in the DB"""
        for tc in test_cases:
            classification = self.classify(tc)
            tc.type = classification
            
            # Update in Supabase
            if self.supabase.client:
                try:
                    self.supabase.client.table('test_cases').update({'type': classification}).eq('id', tc.id).execute()
                except Exception as e:
                    print(f"Failed to update classification for {tc.id}: {e}")
