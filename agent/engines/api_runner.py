import time
import httpx
from typing import Any
import uuid
from ..models import TestCase, TestResult
from ..config import settings

class APIRunner:
    def __init__(self):
        self.base_url = settings.TARGET_APP_URL.rstrip('/')
        
    async def execute(self, test_case: TestCase, run_id: str) -> TestResult:
        print(f"Executing Backend Test: {test_case.name}")
        start_time = time.time()
        
        # Extract API details from test_data or try to infer
        data = test_case.test_data or {}
        method = data.get('method', 'GET').upper()
        endpoint = data.get('endpoint', '/')
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
            
        url = f"{self.base_url}{endpoint}"
        headers = data.get('headers', {})
        payload = data.get('payload', None)
        
        status = 'error'
        error_msg = None
        logs = []
        response_data = None
        
        logs.append({"action": "request", "method": method, "url": url})
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=payload if method in ['POST', 'PUT', 'PATCH'] else None,
                    headers=headers,
                    timeout=10.0
                )
                
                logs.append({"action": "response", "status_code": response.status_code})
                
                try:
                    response_data = response.json()
                except Exception:
                    response_data = response.text
                
                # Basic assertion logic (simplified for demo)
                # In reality, this would evaluate the 'assertions' list against response_data
                expected_status = data.get('expected_status', 200)
                if response.status_code == expected_status:
                    status = 'pass'
                else:
                    status = 'fail'
                    error_msg = f"Expected status {expected_status}, got {response.status_code}"
                    
        except httpx.RequestError as exc:
            error_msg = f"An error occurred while requesting {exc.request.url!r}."
            logs.append({"error": error_msg})
        except Exception as e:
            error_msg = str(e)
            logs.append({"error": error_msg})
            
        duration = time.time() - start_time
        
        return TestResult(
            id=str(uuid.uuid4()),
            test_case_id=test_case.id,
            test_run_id=run_id,
            status=status,
            logs=logs,
            payload={"request": payload, "response": response_data},
            duration_seconds=round(duration, 2),
            error_message=error_msg
        )
