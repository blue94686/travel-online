from app.core.database import get_db


def write_audit(module: str, action: str, operator: str = "admin", ip: str = "127.0.0.1", result: str = "success"):
    with get_db() as db:
        db.execute(
            "INSERT INTO audit_logs (operator,module,action,ip,result) VALUES (?,?,?,?,?)",
            (operator, module, action, ip, result),
        )
