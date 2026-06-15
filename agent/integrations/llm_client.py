from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from browser_use import ChatAnthropic as AgentChatAnthropic, ChatGoogle as AgentChatGoogle
from ..config import settings

from pydantic import Field

class BrowserUseAnthropic(ChatAnthropic):
    @property
    def provider(self) -> str:
        return 'anthropic'

    @property
    def model_name(self) -> str:
        return self.model

class BrowserUseGoogle(ChatGoogleGenerativeAI):
    @property
    def provider(self) -> str:
        return 'google'

    @property
    def model_name(self) -> str:
        return self.model

class LLMClient:
    def __init__(self, provider_override: str = None):
        """
        Initializes the LLM client based on provider logic.
        1. Uses provider_override (from CLI flag --gemini or --claude) if provided.
        2. Otherwise, uses settings.DEFAULT_LLM (from config).
        3. Fallback logic: If Anthropic is requested but no key exists, fall back to Gemini (and vice versa).
        """
        # Determine intended provider
        provider = provider_override if provider_override else settings.DEFAULT_LLM
        provider = provider.lower()

        # Fallback routing
        if provider == "claude" and not settings.ANTHROPIC_API_KEY:
            print("Warning: Anthropic API Key not found. Falling back to Gemini.")
            provider = "gemini"

        elif provider == "gemini" and not settings.GOOGLE_API_KEY:
            print("Warning: Google API Key not found. Falling back to Claude.")
            provider = "claude"

        self.provider = provider

        if self.provider == "claude":
            if not settings.ANTHROPIC_API_KEY:
                print("Error: No API keys configured for any LLM provider.")
                self.llm = None
                self.haiku_llm = None
                self.browser_llm = None
            else:
                self.llm = BrowserUseAnthropic(
                    model="claude-sonnet-4-6",
                    api_key=settings.ANTHROPIC_API_KEY,
                    temperature=0.2,
                    max_tokens=16000
                )
                self.haiku_llm = BrowserUseAnthropic(
                    model="claude-3-5-haiku-20241022",
                    api_key=settings.ANTHROPIC_API_KEY,
                    temperature=0.2
                )
                # Native browser-use LLM (incompatible with langchain interface used by generator/classifier)
                self.browser_llm = AgentChatAnthropic(
                    model="claude-sonnet-4-6",
                    api_key=settings.ANTHROPIC_API_KEY,
                    temperature=0.2,
                    max_tokens=16000
                )
        else:
            # Gemini Provider
            if not settings.GOOGLE_API_KEY:
                print("Error: No API keys configured for any LLM provider.")
                self.llm = None
                self.haiku_llm = None
                self.browser_llm = None
            else:
                self.llm = BrowserUseGoogle(
                    model="gemini-3.5-flash",
                    google_api_key=settings.GOOGLE_API_KEY,
                    temperature=0.2
                )
                self.haiku_llm = BrowserUseGoogle(
                    model="gemini-3.5-flash",
                    google_api_key=settings.GOOGLE_API_KEY,
                    temperature=0.2
                )
                # Native browser-use LLM — uses api_key (not google_api_key)
                self.browser_llm = AgentChatGoogle(
                    model="gemini-2.0-flash",
                    api_key=settings.GOOGLE_API_KEY,
                    temperature=0.2
                )

    def get_sonnet(self):
        """Returns the primary complex model (Sonnet or Gemini Pro) — langchain interface"""
        return self.llm

    def get_haiku(self):
        """Returns the faster/cheaper model (Haiku or Gemini Flash) — langchain interface"""
        return self.haiku_llm

    def get_browser_llm(self):
        """Returns the native browser-use LLM for the browser agent (incompatible with langchain)"""
        return self.browser_llm
