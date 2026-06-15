import os
import time
import uuid
import asyncio
from typing import Any
from browser_use import Agent, Browser
from ..models import TestCase, TestResult
from ..integrations.supabase_client import SupabaseClient
from ..integrations.llm_client import LLMClient
from ..config import settings

class BrowserRunner:
    def __init__(self, headless: bool = False):
        self.supabase = SupabaseClient()
        self.base_url = settings.TARGET_APP_URL
        self.headless = headless
        
        # Browser-Use specific LLM, routes through our central factory
        self.agent_llm = LLMClient().get_sonnet()

    def _build_task_prompt(self, test_case: TestCase) -> str:
        """Converts structured test case into a prompt for Browser Use"""
        prompt = f"Navigate to {self.base_url}. "
        prompt += "Your goal is to execute the following test case steps and verify the assertions:\n\n"
        
        prompt += "STEPS:\n"
        for i, step in enumerate(test_case.steps, 1):
            prompt += f"{i}. {step}\n"
            
        prompt += "\nASSERTIONS (You must verify these are true):\n"
        for i, assertion in enumerate(test_case.assertions, 1):
            prompt += f"- {assertion}\n"
            
        if test_case.test_data:
            prompt += f"\nTEST DATA TO USE:\n{test_case.test_data}\n"
            
        prompt += "\nIf the assertions pass, finish the task. If any assertion fails, explain why in your final response."
        return prompt

    async def execute(self, test_case: TestCase, run_id: str) -> TestResult:
        """Executes a single frontend test case using Browser Use"""
        
        print(f"Executing Frontend Test: {test_case.name}")
        start_time = time.time()
        
        task_prompt = self._build_task_prompt(test_case)
        
        from browser_use import BrowserConfig
        auth_file = os.path.abspath("auth.json")
        if os.path.exists(auth_file):
            print(f"🔑 Found saved session. Injecting authentication state from {auth_file}")
            browser = Browser(config=BrowserConfig(headless=self.headless, state_path=auth_file))
        else:
            browser = Browser(config=BrowserConfig(headless=self.headless))
        agent = Agent(
            task=task_prompt,
            llm=self.agent_llm,
            browser=browser,
            max_failures=1, # Fail fast instead of wasting 1-2 mins retrying bad paths
            generate_gif=False # GIF generation takes 10-20 seconds post-test, disable for speed
        )
        
        status = "error"
        error_msg = None
        logs = []
        screenshot_url = None
        cost = 0.0
        
        try:
            # Run the autonomous loop
            result = await agent.run()
            
            # The result contains history and final status
            cost = getattr(result, 'total_cost', lambda: 0.0)() if callable(getattr(result, 'total_cost', None)) else 0.0
            history_logs = [str(action) for action in result.history] if hasattr(result, 'history') else []
            logs.extend(history_logs)
            
            # Fix: AgentHistoryList uses is_successful() instead of success
            is_success = result.is_successful() if hasattr(result, 'is_successful') else False
            
            if is_success:
                status = "pass"
            else:
                status = "fail"
                # Extract the reason for failure from the agent's final reasoning
                if hasattr(result, 'final_result'):
                    error_msg = result.final_result()
                elif hasattr(result, 'errors') and result.errors():
                    error_msg = str(result.errors()[-1])
                else:
                    error_msg = "Agent evaluated the test assertions as FAILED."
                
            # Capture screenshot on failure
            if status == "fail":
                os.makedirs("screenshots", exist_ok=True)
                file_name = f"fail_{test_case.id}_{int(time.time())}.png"
                file_path = os.path.join("screenshots", file_name)
                
        except Exception as e:
            error_msg = str(e)
            logs.append(f"Fatal error: {error_msg}")
        finally:
            # Clean up the browser instance
            await browser.close()
            
        duration = time.time() - start_time
        
        # Save cost to run if needed, but we track cost at the run level usually
        
        return TestResult(
            id=str(uuid.uuid4()),
            test_case_id=test_case.id,
            test_run_id=run_id,
            status=status,
            logs=logs,
            duration_seconds=round(duration, 2),
            cost=round(cost, 4),
            error_message=error_msg,
            screenshot_url=screenshot_url
        )
