from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class TestResult(BaseModel):
    id: str = Field(..., description="A unique identifier for this result")
    test_case_id: str = Field(..., description="The ID of the test case executed")
    test_run_id: str = Field(..., description="The ID of the broader test run execution")
    status: str = Field(..., description="Result status: 'pass', 'fail', 'skip', or 'error'")
    screenshot_url: Optional[str] = Field(None, description="URL of the failure screenshot (if any)")
    logs: list[Any] = Field(default_factory=list, description="Execution history/logs from the agent")
    payload: Optional[Dict[str, Any]] = Field(None, description="API request/response payload for backend tests")
    duration_seconds: float = Field(0.0, description="Time taken to execute the test")
    error_message: Optional[str] = Field(None, description="Error message if the test failed or errored")
    executed_at: datetime = Field(default_factory=datetime.utcnow)

class TestRun(BaseModel):
    id: str = Field(..., description="A unique identifier for this test run")
    status: str = Field(default="running", description="'running', 'completed', or 'failed'")
    total_tests: int = Field(0, description="Total test cases to be executed")
    passed: int = Field(0, description="Number of passed tests")
    failed: int = Field(0, description="Number of failed tests")
    duration_seconds: float = Field(0.0, description="Total execution time")
    api_cost_usd: float = Field(0.0, description="Cost of Claude API calls for this run")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
