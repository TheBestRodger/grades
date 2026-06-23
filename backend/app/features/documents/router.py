from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from ...api.deps import current_actor, current_hr, get_document_storage_dir, get_session
from ...api.errors import run_operation
from ...models import Employee
from .schemas import WorkDocumentLinkUpdate, WorkDocumentQualityUpdate
from .service import (
    get_document_registry,
    get_manager_document_registry,
    get_work_document_source,
    review_work_document_quality,
    set_work_document_link,
    upload_work_document,
)

router = APIRouter()


@router.get("/api/hr/documents")
def documents(_: Employee = Depends(current_hr), session: Session = Depends(get_session)) -> dict[str, object]:
    return get_document_registry(session)


@router.get("/api/work/hr/documents")
def work_documents(_: Employee = Depends(current_hr), session: Session = Depends(get_session)) -> dict[str, object]:
    return get_document_registry(session, is_demo=False)


@router.put("/api/work/hr/documents/link")
def update_work_document_link(
    request: WorkDocumentLinkUpdate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return run_operation(lambda: set_work_document_link(session, actor, request))


@router.post("/api/work/hr/documents/upload")
async def upload_work_document_file(
    request: Request,
    filename: str,
    document_code: str,
    document_type: str,
    title: str,
    version: str = "1.0",
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
    document_storage_dir: Path = Depends(get_document_storage_dir),
) -> dict[str, object]:
    content = await request.body()
    return run_operation(
        lambda: upload_work_document(
            session,
            actor,
            document_storage_dir,
            filename=filename,
            document_code=document_code,
            document_type=document_type,
            title=title,
            version=version,
            content=content,
        )
    )


@router.put("/api/work/hr/documents/{document_id}/quality")
def update_work_document_quality(
    document_id: int,
    request: WorkDocumentQualityUpdate,
    actor: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
    document_storage_dir: Path = Depends(get_document_storage_dir),
) -> dict[str, object]:
    return run_operation(
        lambda: review_work_document_quality(session, actor, document_storage_dir, document_id, request)
    )


@router.get("/api/work/hr/documents/{document_id}/source")
def download_work_document_source(
    document_id: int,
    _: Employee = Depends(current_hr),
    session: Session = Depends(get_session),
    document_storage_dir: Path = Depends(get_document_storage_dir),
) -> Response:
    content, filename, media_type = run_operation(
        lambda: get_work_document_source(session, document_storage_dir, document_id)
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/manager/documents")
def manager_documents(
    actor: Employee = Depends(current_actor), session: Session = Depends(get_session)
) -> dict[str, object]:
    return run_operation(lambda: get_manager_document_registry(session, actor))
