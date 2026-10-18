from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sentinela.db import connect

GENESIS_HASH = "0" * 64


def _canonical(event: dict) -> bytes:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def append_event(
    conn,
    *,
    actor_id: int | None,
    action: str,
    resource_type: str,
    resource_id: str | None,
    outcome: str,
    reason_code: str,
) -> None:
    previous = conn.execute(
        "SELECT event_hash FROM audit_events ORDER BY seq DESC LIMIT 1"
    ).fetchone()
    prev_hash = previous["event_hash"] if previous else GENESIS_HASH
    timestamp = datetime.now(UTC).isoformat()
    core = {
        "timestamp": timestamp,
        "actor_id": actor_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "outcome": outcome,
        "reason_code": reason_code,
        "prev_hash": prev_hash,
    }
    event_hash = hashlib.sha256(_canonical(core)).hexdigest()
    conn.execute(
        "INSERT INTO audit_events(timestamp,actor_id,action,resource_type,resource_id,outcome,reason_code,prev_hash,event_hash) VALUES(?,?,?,?,?,?,?,?,?)",
        (
            timestamp,
            actor_id,
            action,
            resource_type,
            resource_id,
            outcome,
            reason_code,
            prev_hash,
            event_hash,
        ),
    )


def verify_ledger(path: str) -> dict[str, int | bool | str]:
    conn = connect(path)
    try:
        rows = conn.execute("SELECT * FROM audit_events ORDER BY seq").fetchall()
    finally:
        conn.close()
    previous = GENESIS_HASH
    for expected_seq, row in enumerate(rows, start=1):
        if row["seq"] != expected_seq or row["prev_hash"] != previous:
            return {"valid": False, "events_checked": expected_seq - 1, "failed_seq": row["seq"]}
        core = {
            key: row[key]
            for key in (
                "timestamp",
                "actor_id",
                "action",
                "resource_type",
                "resource_id",
                "outcome",
                "reason_code",
                "prev_hash",
            )
        }
        actual = hashlib.sha256(_canonical(core)).hexdigest()
        if actual != row["event_hash"]:
            return {"valid": False, "events_checked": expected_seq - 1, "failed_seq": row["seq"]}
        previous = row["event_hash"]
    return {"valid": True, "events_checked": len(rows), "failed_seq": ""}
