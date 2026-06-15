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

import logging

# Suppress the buggy browser-use warning about user_data_dir which spams the console
class BrowserUseWarningFilter(logging.Filter):
    def filter(self, record):
        return "was passed both storage_state AND user_data_dir" not in record.getMessage()

logging.getLogger("browser_use.utils").addFilter(BrowserUseWarningFilter())

class BrowserRunner:
    def __init__(self, headless: bool = False):
        self.supabase = SupabaseClient()
        self.base_url = settings.TARGET_APP_URL
        self.headless = headless
        
        # Native browser-use LLM (generator/classifier use the langchain one via get_sonnet())
        self.agent_llm = LLMClient().get_browser_llm()
        
        auth_file = os.path.abspath("auth.json")
        if os.path.exists(auth_file):
            print(f"🔑 Found saved session. Will inject authentication state from {auth_file} into all parallel browsers.")

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
        
        MAX_ATTEMPTS = 3  # 1 initial run + 2 retries for crashes only
        auth_file = os.path.abspath("auth.json")

        status = "error"
        error_msg = None
        logs = []
        screenshot_url = None
        cost = 0.0

        for attempt in range(1, MAX_ATTEMPTS + 1):
            if os.path.exists(auth_file):
                browser = Browser(headless=self.headless, storage_state=auth_file, user_data_dir=None)
            else:
                browser = Browser(headless=self.headless, user_data_dir=None)

            agent = Agent(
                task=task_prompt,
                llm=self.agent_llm,
                browser=browser,
                max_failures=3,
                generate_gif=False
            )

            try:
                result = await agent.run()

                cost = getattr(result, 'total_cost', lambda: 0.0)() if callable(getattr(result, 'total_cost', None)) else 0.0
                history_logs = [str(action) for action in result.history] if hasattr(result, 'history') else []
                logs.extend(history_logs)

                is_success = result.is_successful() if hasattr(result, 'is_successful') else None

                if is_success is True:
                    status = "pass"
                    break  # genuine pass — do not retry
                elif is_success is False:
                    # Agent ran and explicitly judged the assertions as failed
                    status = "fail"
                    if hasattr(result, 'final_result') and result.final_result():
                        error_msg = result.final_result()
                    elif hasattr(result, 'errors') and result.errors():
                        error_msg = str(next((e for e in reversed(result.errors()) if e), None))
                    else:
                        error_msg = "Agent evaluated the test assertions as FAILED."
                    break  # genuine fail — do not retry
                else:
                    # is_successful() is None: agent never called done (crash, max-failures, max-steps)
                    status = "error"
                    if hasattr(result, 'errors') and result.errors():
                        error_msg = str(next((e for e in reversed(result.errors()) if e), None) or "Agent did not complete the run (no done action).")
                    else:
                        error_msg = "Agent did not complete the run (no done action)."
                    if attempt < MAX_ATTEMPTS:
                        print(f"  ⚠️  Attempt {attempt}/{MAX_ATTEMPTS} did not complete — retrying...")

            except Exception as e:
                status = "error"
                error_msg = str(e)
                logs.append(f"Fatal error (attempt {attempt}): {error_msg}")
                if attempt < MAX_ATTEMPTS:
                    print(f"  ⚠️  Attempt {attempt}/{MAX_ATTEMPTS} raised an exception — retrying...")
            finally:
                await browser.close()

            if status in ("pass", "fail"):
                break

        duration = time.time() - start_time

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
