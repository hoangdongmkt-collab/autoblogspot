import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import RecoveryTask, Article, Project
from ..templates import templates

router = APIRouter()


@router.get("/recovery", response_class=HTMLResponse)
def recovery_page(
    request: Request,
    status: str = Query(None),
    page: str = Query("1"),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    try:
        page_num = max(1, int(page))
    except (ValueError, TypeError):
        page_num = 1

    per_page = 30
    base = (
        db.query(RecoveryTask)
        .filter(RecoveryTask.user_id == current_user.id)
    )
    if status:
        base = base.filter(RecoveryTask.status == status)

    total = base.count()
    tasks = base.order_by(RecoveryTask.created_at.desc()).offset((page_num - 1) * per_page).limit(per_page).all()

    counts = {}
    for s in ("pending", "processing", "done", "failed", "not_found"):
        counts[s] = (
            db.query(RecoveryTask)
            .filter(RecoveryTask.user_id == current_user.id, RecoveryTask.status == s)
            .count()
        )
    counts["all"] = sum(counts.values())

    return templates.TemplateResponse(request, "recovery.html", {
        "tasks":         tasks,
        "counts":        counts,
        "total":         total,
        "page":          page_num,
        "per_page":      per_page,
        "total_pages":   max(1, (total + per_page - 1) // per_page),
        "filter_status": status,
        "current_user":  current_user,
        "active_page":   "recovery",
    })


@router.post("/recovery/submit")
def submit_recovery_urls(
    request: Request,
    urls_text: str = Form(""),
    db: Session = Depends(get_db),
):
    current_user = get_current_user(request, db)
    uid = current_user.id

    added = 0
    skipped = 0
    for line in urls_text.splitlines():
        url = line.strip()
        if not url or not url.startswith("http"):
            continue
        url = url.rstrip("/")  # normalize trailing slash

        # Skip if already in queue (pending or processing)
        existing = (
            db.query(RecoveryTask)
            .filter(
                RecoveryTask.user_id == uid,
                RecoveryTask.url == url,
                RecoveryTask.status.in_(["pending", "processing"]),
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        db.add(RecoveryTask(user_id=uid, url=url, status="pending"))
        added += 1

    db.commit()

    if added:
        return RedirectResponse(
            f"/recovery?success=Da+them+{added}+URL+vao+hang+cho+xu+ly",
            status_code=303,
        )
    return RedirectResponse(
        f"/recovery?error=Khong+them+duoc+URL+nao+{skipped}+da+ton+tai",
        status_code=303,
    )


@router.post("/recovery/{task_id}/retry")
def retry_recovery_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    task = (
        db.query(RecoveryTask)
        .filter(RecoveryTask.id == task_id, RecoveryTask.user_id == current_user.id)
        .first()
    )
    if task and task.status in ("failed", "not_found"):
        task.status = "pending"
        task.error_message = None
        task.processed_at = None
        db.commit()
    return RedirectResponse("/recovery?success=Da+them+vao+hang+cho+xu+ly+lai", status_code=303)


@router.post("/recovery/{task_id}/delete")
def delete_recovery_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    task = (
        db.query(RecoveryTask)
        .filter(RecoveryTask.id == task_id, RecoveryTask.user_id == current_user.id)
        .first()
    )
    if task:
        db.delete(task)
        db.commit()
    return RedirectResponse("/recovery", status_code=303)


@router.get("/recovery/export")
def export_recovery_csv(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    tasks = (
        db.query(RecoveryTask)
        .filter(RecoveryTask.user_id == current_user.id)
        .order_by(RecoveryTask.created_at.desc())
        .all()
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "URL", "Trạng thái", "Lỗi", "Tạo lúc", "Xử lý lúc"])
    for t in tasks:
        writer.writerow([
            t.id, t.url, t.status,
            t.error_message or "",
            t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "",
            t.processed_at.strftime("%Y-%m-%d %H:%M") if t.processed_at else "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=recovery.csv"},
    )
