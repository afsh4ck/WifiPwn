from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.wifi_manager import wifi_manager
from core.utils import run_command

router = APIRouter()


class MonitorRequest(BaseModel):
    interface: str


class MacRequest(BaseModel):
    interface: str
    mac: str = None   # None = random


@router.get("/")
async def list_interfaces():
    interfaces = wifi_manager.get_interfaces()
    result = []
    for iface in interfaces:
        name = iface.get("name", "")
        info = wifi_manager.get_interface_info(name)
        result.append({**iface, **info})
    return result


@router.get("/{name}")
async def get_interface(name: str):
    return wifi_manager.get_interface_info(name)


@router.post("/monitor/enable")
async def enable_monitor(req: MonitorRequest):
    ok, msg = wifi_manager.enable_monitor_mode(req.interface)
    if not ok:
        raise HTTPException(status_code=500, detail=msg)
    return {"success": True, "monitor_interface": wifi_manager.monitor_interface, "message": msg}


@router.post("/monitor/disable")
async def disable_monitor(req: MonitorRequest):
    ok, msg = wifi_manager.disable_monitor_mode(req.interface)
    return {"success": ok, "message": msg}


@router.post("/kill-processes")
async def kill_conflicting():
    rc, stdout, stderr = run_command(["airmon-ng", "check", "kill"])
    return {"success": rc == 0, "output": stdout or stderr}


@router.post("/reset")
async def reset_interface(req: MonitorRequest):
    run_command(["ip", "link", "set", req.interface, "down"])
    rc, _, stderr = run_command(["ip", "link", "set", req.interface, "up"])
    return {"success": rc == 0, "error": stderr}


@router.post("/mac/change")
async def change_mac(req: MacRequest):
    from core.utils import generate_random_mac
    mac = req.mac or generate_random_mac()
    run_command(["ip", "link", "set", req.interface, "down"])
    rc, _, stderr = run_command(["macchanger", "-m", mac, req.interface])
    run_command(["ip", "link", "set", req.interface, "up"])
    return {"success": rc == 0, "new_mac": mac, "error": stderr}
