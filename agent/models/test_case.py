from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class TestCase(BaseModel):
    id: str = Field(..., description="A unique identifier for the test case")
    ticket_id: str = Field(..., description="The ID of the ticket this test case belongs to")
    name: str = Field(..., description="Descriptive name of the test case")
    type: str = Field(..., description="Whether this tests the UI or API, or custom type from sheet")
    priority: str = Field(default="medium", description="Severity/Priority of the test case")
    automation_status: Optional[str] = Field(default=None, description="Manual, Playwright, API, etc.")
    steps: List[str] = Field(default_factory=list, description="Ordered steps to execute the test")
    assertions: List[str] = Field(default_factory=list, description="What to verify after steps are executed")
    test_data: Dict[str, Any] = Field(default_factory=dict, description="Input data needed for the test")
    ai_generated: bool = Field(default=True, description="Whether Claude generated this case")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # TestRail / RFC fields (populated by generate_from_rfc, optional for ticket flow)
    preconditions: Optional[str] = Field(default=None, description="Prerequisites before test execution")
    expected_result: Optional[str] = Field(default=None, description="Expected outcome in plain text")
    rfc_section: Optional[str] = Field(default=None, description="RFC section / feature this test maps to")
    test_category: Optional[str] = Field(default=None, description="UI/API/Backend/Integration/Security")
    source_test_id: Optional[str] = Field(default=None, description="Original Test ID from the spreadsheet (e.g., VIT-001)")

