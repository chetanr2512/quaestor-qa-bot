import asyncio
from typing import List
from ..models import TestCase, TestResult
from ..engines.api_runner import APIRunner
from ..engines.browser_runner import BrowserRunner
from ..integrations.supabase_client import SupabaseClient

class TestExecutor:
    def __init__(self, headless: bool = False):
        self.api_runner = APIRunner()
        self.browser_runner = BrowserRunner(headless=headless)
        self.supabase = SupabaseClient()

    async def execute_all(self, test_cases: List[TestCase]) -> List[TestResult]:
        if not test_cases:
            print("No test cases to execute.")
            return []
            
        run_id = self.supabase.create_test_run(len(test_cases))
        print(f"Started Test Run: {run_id}")
        
        results = []
        passed = 0
        failed = 0
        total_duration = 0.0
        
        semaphore = asyncio.Semaphore(3) # Max 3 concurrent tests to avoid crashing RAM with browsers
        lock = asyncio.Lock()

        async def run_single_test(tc):
            nonlocal passed, failed, total_duration
            async with semaphore:
                try:
                    # Route to API or Browser runner based on automation_status or type
                    is_api = False
                    if tc.automation_status and 'api' in str(tc.automation_status).lower():
                        is_api = True
                    elif tc.type and str(tc.type).lower() == 'backend':
                        is_api = True
                        
                    if is_api:
                        result = await self.api_runner.execute(tc, run_id)
                    else:
                        result = await self.browser_runner.execute(tc, run_id)
                        
                    async with lock:
                        results.append(result)
                        # Save individual result
                        self.supabase.insert_test_result(result)
                        
                        if result.status == 'pass':
                            passed += 1
                        else:
                            failed += 1
                            
                        total_duration += result.duration_seconds
                        
                        # Update run progress in real-time
                        self.supabase.update_test_run(
                            run_id=run_id,
                            passed=passed,
                            failed=failed,
                            duration=total_duration,
                            cost=0.0,
                            status='running'
                        )
                except Exception as e:
                    print(f"Critical error executing test {tc.name}: {e}")
                    async with lock:
                        failed += 1

        tasks = [run_single_test(tc) for tc in test_cases]
        await asyncio.gather(*tasks)
                
        # Finalize run
        print(f"Test Run Completed. Passed: {passed}, Failed: {failed}")
        self.supabase.update_test_run(
            run_id=run_id,
            passed=passed,
            failed=failed,
            duration=total_duration,
            cost=0.0,
            status='completed'
        )
        
        return results
