from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class Ticket(BaseModel):
    id: str = Field(..., description="A unique identifier for the ticket (e.g., Jira issue key or UUID)")
    title: str = Field(..., description="The summary or title of the ticket")
    description: str = Field(..., description="The full details and requirements of the ticket")
    source: str = Field(..., description="Where the ticket came from (e.g., 'jira', 'sheets', 'docs')")
    source_id: str = Field(..., description="The original ID in the source system")
    status: str = Field(default="open", description="Current status of the ticket")
    created_at: datetime = Field(default_factory=datetime.utcnow)
