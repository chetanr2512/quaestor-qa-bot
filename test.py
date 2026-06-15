from langchain_anthropic import ChatAnthropic
from pydantic import Field

class BrowserUseAnthropic(ChatAnthropic):
    provider: str = Field(default='anthropic')

llm = BrowserUseAnthropic(model='claude-3-5-sonnet-20241022', api_key='mock')
print(llm.provider)
