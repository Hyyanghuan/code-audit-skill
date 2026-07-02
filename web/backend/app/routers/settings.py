from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.schemas import ApplyPresetBody, AuditSettingsBody, TelegramSettingsBody
from app.services.audit_settings import (
    apply_preset_to_settings,
    get_audit_settings,
    save_audit_settings,
)
from app.services.telegram_client import get_telegram_settings, save_telegram_settings
from app.settings_catalog import (
    AUDIT_GROUPS,
    TELEGRAM_GROUPS,
    get_tool_path_suggestions,
    list_presets_meta,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/catalog")
def settings_catalog(_: str = Depends(get_current_user)):
    return {
        "audit_groups": AUDIT_GROUPS,
        "telegram_groups": TELEGRAM_GROUPS,
        "presets": list_presets_meta(),
        "tool_path_suggestions": get_tool_path_suggestions(),
    }


@router.get("/audit")
def read_audit_settings(_: str = Depends(get_current_user)):
    return {"values": get_audit_settings()}


@router.put("/audit")
def update_audit_settings(body: AuditSettingsBody, _: str = Depends(get_current_user)):
    saved = save_audit_settings(body.values)
    return {"values": saved}


@router.post("/audit/apply-preset")
def apply_preset(body: ApplyPresetBody, _: str = Depends(get_current_user)):
    if body.preset not in {p["id"] for p in list_presets_meta()}:
        raise HTTPException(400, f"未知预设: {body.preset}")
    saved = apply_preset_to_settings(body.preset)
    return {"values": saved}


@router.get("/telegram")
def read_telegram(_: str = Depends(get_current_user)):
    return {"values": get_telegram_settings()}


@router.put("/telegram")
def update_telegram(body: TelegramSettingsBody, _: str = Depends(get_current_user)):
    saved = save_telegram_settings(body.values)
    return {"values": saved}
