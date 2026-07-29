from datetime import datetime

from pydantic import BaseModel


class AppSettingOut(BaseModel):
    key: str
    value: dict
    updated_at: datetime

    model_config = {"from_attributes": True}


class AppSettingUpsert(BaseModel):
    value: dict
