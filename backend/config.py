"""
Configuration settings for the backend application.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Property Management System API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Database - acepta tanto DB_* como MYSQL_*
    DB_HOST: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = None
    DB_NAME: Optional[str] = None
    DB_PORT: int = 3306
    
    # Alternativas para compatibilidad
    MYSQL_HOST: Optional[str] = None
    MYSQL_USER: Optional[str] = None
    MYSQL_PASSWORD: Optional[str] = None
    MYSQL_DATABASE: Optional[str] = None
    MYSQL_PORT: Optional[str] = None
    
    # Electric allowance bookings (comma-separated list)
    ELECTRIC: str = ""
    
    # API
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Permite campos extra
    
    def model_post_init(self, __context):
        """Post-initialization to handle both DB_* and MYSQL_* prefixes."""
        # Si MYSQL_* está definido pero DB_* no, usar MYSQL_*
        if self.MYSQL_HOST and not self.DB_HOST:
            self.DB_HOST = self.MYSQL_HOST
        if self.MYSQL_USER and not self.DB_USER:
            self.DB_USER = self.MYSQL_USER
        if self.MYSQL_PASSWORD and not self.DB_PASS:
            self.DB_PASS = self.MYSQL_PASSWORD
        if self.MYSQL_DATABASE and not self.DB_NAME:
            self.DB_NAME = self.MYSQL_DATABASE
        if self.MYSQL_PORT and not isinstance(self.DB_PORT, int):
            self.DB_PORT = int(self.MYSQL_PORT)


# Global settings instance
settings = Settings()