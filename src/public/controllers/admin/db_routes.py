"""Database admin routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from typing import Any, Dict, List, Optional

from src.core.database import get_db
from src.domain.models import User
from .dependencies import get_current_admin

router = APIRouter(prefix="/database", tags=["Admin Database"])


class QueryRequest(BaseModel):
    query: str
    params: Optional[Dict[str, Any]] = None


@router.get("/tables")
def list_tables(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()
    result = []
    for table in tables:
        columns = inspector.get_columns(table)
        result.append({
            "name": table,
            "column_count": len(columns),
        })
    return {"tables": result}


@router.get("/table/{table_name}")
def get_table_data(
    table_name: str,
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    inspector = inspect(db.bind)
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail="Table not found")
    offset = (page - 1) * per_page
    total_result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
    total = total_result.scalar() or 0
    rows_result = db.execute(text(f"SELECT * FROM {table_name} LIMIT :limit OFFSET :offset"), {"limit": per_page, "offset": offset})
    columns = list(rows_result.keys())
    rows = [dict(zip(columns, row)) for row in rows_result.fetchall()]
    return {"table": table_name, "rows": rows, "total": total, "page": page, "per_page": per_page}


@router.get("/table/{table_name}/schema")
def get_table_schema(
    table_name: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    inspector = inspect(db.bind)
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail="Table not found")
    columns = inspector.get_columns(table_name)
    pk = inspector.get_pk_constraint(table_name)
    indexes = inspector.get_indexes(table_name)
    fks = inspector.get_foreign_keys(table_name)
    return {
        "table": table_name,
        "columns": [{"name": c["name"], "type": str(c["type"]), "nullable": c.get("nullable", True)} for c in columns],
        "primary_key": pk,
        "indexes": indexes,
        "foreign_keys": fks,
    }


@router.get("/stats")
def database_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()
    table_stats = []
    for table in tables:
        count_result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = count_result.scalar() or 0
        table_stats.append({"name": table, "row_count": count})
    return {"total_tables": len(tables), "tables": table_stats}


@router.post("/query")
def execute_query(
    data: QueryRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query_lower = data.query.strip().lower()
    if not query_lower.startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    try:
        result = db.execute(text(data.query), data.params or {})
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return {"columns": columns, "rows": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/optimize")
def optimize_database(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        db.execute(text("VACUUM"))
        return {"status": "optimized"}
    except Exception:
        return {"status": "ok", "note": "VACUUM not supported on this database engine"}
