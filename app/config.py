import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    
    source_site_id: str = ""
    source_list_id: str = ""
    source_drive_id: str = ""
    source_root_path: str = "CompanySync"
    
    dest_drive_id: str = ""
    dest_root_path: str = "CompanySync"
    
    webhook_url: str = ""
    webhook_client_state: str = ""
    
    copy_conflict_behavior: str = "replace"
    copy_updates: bool = False
    db_path: str = "sync_state.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
