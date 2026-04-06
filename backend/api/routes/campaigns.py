from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from core.database import db

router = APIRouter()


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class TargetAdd(BaseModel):
    network_id: int
    notes: Optional[str] = ""


@router.get("/")
async def list_campaigns():
    return db.get_campaigns()


@router.post("/")
async def create_campaign(req: CampaignCreate):
    cid = db.create_campaign(req.name, req.description)
    db.log_action("Campaña creada", req.name)
    return {"id": cid, "name": req.name}


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: int, req: CampaignUpdate):
    db.update_campaign(campaign_id, req.name, req.description, req.status)
    return {"success": True}


@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: int):
    db.delete_campaign(campaign_id)
    return {"success": True}


@router.get("/{campaign_id}/targets")
async def get_targets(campaign_id: int):
    return db.get_campaign_targets(campaign_id)


@router.post("/{campaign_id}/targets")
async def add_target(campaign_id: int, req: TargetAdd):
    db.add_campaign_target(campaign_id, req.network_id, req.notes)
    return {"success": True}


@router.get("/{campaign_id}/report")
async def generate_report(campaign_id: int):
    campaigns = db.get_campaigns()
    campaign  = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    targets = db.get_campaign_targets(campaign_id)
    return {
        "campaign": campaign,
        "targets":  targets,
        "stats":    db.get_statistics(),
    }
