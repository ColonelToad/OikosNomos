import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "oikosnomo_dev"
    db_name: str = "oikosnomo"
    
    class Config:
        env_file = ".env"

settings = Settings()
