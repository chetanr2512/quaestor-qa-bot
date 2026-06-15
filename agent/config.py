import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    
    # Google (Gemini)
    GOOGLE_API_KEY: str = ""
    
    # LLM Settings
    DEFAULT_LLM: str = "claude" # Can be 'claude' or 'gemini'
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SECRET_KEY: str = ""
    
    # Jira
    JIRA_URL: str = ""
    JIRA_EMAIL: str = ""
    JIRA_API_TOKEN: str = ""
    
    # App Settings
    TARGET_APP_URL: str = "https://qa-assignment-steel.vercel.app/"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
