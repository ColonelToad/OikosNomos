import os
from pydantic_settings import BaseSettings

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = ""

    # Anthropic (optional)
    anthropic_api_key: str = ""

    # Groq (optional)
    groq_api_key: str = ""

    # LLM Provider: "openai", "anthropic", or "groq"
    llm_provider: str = "openai"

    # Model names
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    
    # Database settings
    db_host: str = "timescaledb"
    db_port: int = 5432  # Note: int, not str
    db_user: str = "postgres"
    db_password: str = "oikosnomo_dev"
    db_name: str = "oikosnomo"
    
    # MQTT settings
    mqtt_broker: str = "mosquitto:1883"
    mqtt_client_id: str = "oikosnomo_client"
    
    # Service URLs
    forecast_service_url: str = "http://forecast-service:8000"
    scenario_service_url: str = "http://scenario-service:8000"
    billing_engine_url: str = "http://forecast-service:8000"
    
    # Paths
    docs_dir: str = "docs"
    chroma_dir: str = "chroma_data"
    
    # RAG settings
    chunk_size: int = 500
    chunk_overlap: int = 50
    retrieval_k: int = 5
    
    class Config:
        env_file = ".env"

settings = Settings()