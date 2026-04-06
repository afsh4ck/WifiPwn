import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.command_runner import command_manager
from core.database import db

router = APIRouter()


class CrackRequest(BaseModel):
    cap_file: str
    wordlist: str
    bssid: Optional[str] = None
    tool: str = "aircrack-ng"   # or "hashcat"


class CrackResult(BaseModel):
    cmd_id: str


@router.post("/start")
async def start_cracking(req: CrackRequest):
    if not os.path.exists(req.cap_file):
        raise HTTPException(status_code=400, detail=f"Archivo no encontrado: {req.cap_file}")
    if not os.path.exists(req.wordlist):
        raise HTTPException(status_code=400, detail=f"Wordlist no encontrado: {req.wordlist}")

    if req.tool == "hashcat":
        cmd = ["hashcat", "-m", "22000", req.cap_file, req.wordlist,
               "--force", "--status", "--status-timer=2"]
    else:
        cmd = ["aircrack-ng", "-w", req.wordlist]
        if req.bssid:
            cmd += ["-b", req.bssid]
        cmd.append(req.cap_file)

    def on_finish(cmd_id, info):
        if info:
            output = "\n".join(info.output_lines)
            if "KEY FOUND!" in output:
                for line in info.output_lines:
                    if "KEY FOUND!" in line:
                        s = line.find("[")
                        e = line.find("]", s)
                        if s != -1 and e != -1:
                            pwd = line[s + 1:e].strip()
                            if req.bssid:
                                net = db.get_network_by_bssid(req.bssid)
                                if net:
                                    hs = db.get_handshakes(net["id"])
                                    if hs:
                                        db.crack_handshake(hs[0]["id"], pwd, req.wordlist)
                            db.log_action("Password crackeada", f"BSSID: {req.bssid} Pwd: {pwd}")
                        break

    cmd_id = command_manager.run(cmd, on_finish=on_finish)
    db.log_action("Cracking iniciado", f"BSSID: {req.bssid} Wordlist: {req.wordlist}")
    return {"cmd_id": cmd_id, "command": " ".join(cmd)}


@router.post("/stop/{cmd_id}")
async def stop_cracking(cmd_id: str):
    ok = command_manager.cancel(cmd_id)
    return {"success": ok}


@router.get("/output/{cmd_id}")
async def get_output(cmd_id: str):
    lines = command_manager.get_output(cmd_id)
    info  = command_manager.get_info(cmd_id)
    return {
        "lines":  lines,
        "status": info.status.value if info else "unknown",
    }


@router.get("/handshakes")
async def list_crackable():
    return db.get_handshakes()
