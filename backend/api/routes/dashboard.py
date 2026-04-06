from fastapi import APIRouter
from core.database import db
from core.utils import check_root_privileges

router = APIRouter()

@router.get("/stats")
async def get_stats():
    return db.get_statistics()

@router.get("/logs")
async def get_logs(limit: int = 50):
    return db.get_recent_logs(limit)

@router.get("/status")
async def get_status():
    from core.wifi_manager import wifi_manager
    return {
        "root": check_root_privileges(),
        "current_interface": wifi_manager.current_interface,
        "monitor_interface": wifi_manager.monitor_interface,
        "scanning": wifi_manager._scanning,
        "capturing": wifi_manager._capturing,
    }

@router.delete("/data/{table}")
async def clear_table(table: str):
    ok = db.clear_table(table)
    return {"success": ok}

@router.delete("/data")
async def clear_all():
    ok = db.clear_all()
    return {"success": ok}

@router.get("/export")
async def export_data():
    import tempfile, json
    from datetime import datetime
    from fastapi.responses import FileResponse
    path = f"/tmp/wifipwn_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    db.export_json(path)
    return FileResponse(path, media_type="application/json", filename="wifipwn_export.json")
