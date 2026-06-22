from __future__ import annotations

import re
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.operations import AuditLog, UsageRecord
from app.models.user import User
from app.models.workspace import Department, Permission, Role, RolePermission, WorkspaceMember
from app.services.billing import assert_member_quota
from app.services.bootstrap import ensure_user_workspace

router = APIRouter(prefix="/team", tags=["team"])


class InviteMemberRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    role_code: str = Field(default="member", max_length=80)
    department_id: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("邮箱格式不正确")
        return email


class DepartmentCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    parent_id: str | None = None


class DepartmentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    parent_id: str | None = None


class MemberUpdateRequest(BaseModel):
    role_code: str | None = Field(default=None, max_length=80)
    department_id: str | None = None
    status: str | None = Field(default=None, pattern="^(active|pending|disabled|removed)$")


class RoleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    permission_codes: list[str] | None = None


class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    code: str = Field(..., min_length=2, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    description: str | None = Field(default=None, max_length=500)
    permission_codes: list[str] = Field(default_factory=list)


def _dt(value):
    return value.isoformat() if value else None


def _uuid_or_400(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} 无效") from exc


def _member_payload(member: WorkspaceMember, user: User | None, role: Role | None, department: Department | None) -> dict:
    display = (user.name or user.nickname or user.email) if user else "待激活成员"
    return {
        "id": str(member.id),
        "userId": str(member.user_id) if member.user_id else None,
        "name": display,
        "email": user.email if user else None,
        "phone": user.phone if user else None,
        "role": role.name if role else "成员",
        "roleCode": role.code if role else "member",
        "department": department.name if department else "",
        "departmentId": str(department.id) if department else None,
        "status": member.status,
        "joinedAt": _dt(member.joined_at),
    }


def _department_payload(item: Department) -> dict:
    return {
        "id": str(item.id),
        "name": item.name,
        "parentId": str(item.parent_id) if item.parent_id else None,
        "managerId": str(item.manager_id) if item.manager_id else None,
        "sortOrder": item.sort_order,
        "createdAt": _dt(item.created_at),
    }


async def _get_member_row(db: AsyncSession, workspace_id: uuid.UUID, member_id: str):
    member_uuid = _uuid_or_400(member_id, "member_id")
    result = await db.execute(
        select(WorkspaceMember, User, Role, Department)
        .join(User, WorkspaceMember.user_id == User.id, isouter=True)
        .join(Role, WorkspaceMember.role_id == Role.id, isouter=True)
        .join(Department, WorkspaceMember.department_id == Department.id, isouter=True)
        .where(WorkspaceMember.id == member_uuid, WorkspaceMember.workspace_id == workspace_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="成员不存在")
    return row


async def _get_department(db: AsyncSession, workspace_id: uuid.UUID, department_id: str) -> Department:
    department_uuid = _uuid_or_400(department_id, "department_id")
    item = await db.scalar(
        select(Department).where(Department.id == department_uuid, Department.workspace_id == workspace_id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="部门不存在")
    return item


async def _get_role(db: AsyncSession, workspace_id: uuid.UUID, role_id: str) -> Role:
    role_uuid = _uuid_or_400(role_id, "role_id")
    item = await db.scalar(select(Role).where(Role.id == role_uuid, Role.workspace_id == workspace_id))
    if item is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    return item


@router.get("/overview", response_model=dict)
async def team_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    member_count = await db.scalar(select(func.count(WorkspaceMember.id)).where(WorkspaceMember.workspace_id == workspace.id))
    department_count = await db.scalar(select(func.count(Department.id)).where(Department.workspace_id == workspace.id))
    role_count = await db.scalar(select(func.count(Role.id)).where(Role.workspace_id == workspace.id))
    audit_count = await db.scalar(select(func.count(AuditLog.id)).where(AuditLog.workspace_id == workspace.id))
    usage_total = await db.scalar(
        select(func.coalesce(func.sum(UsageRecord.quantity), Decimal("0"))).where(UsageRecord.workspace_id == workspace.id)
    )
    return {
        "success": True,
        "data": {
            "memberCount": member_count or 0,
            "departmentCount": department_count or 0,
            "roleCount": role_count or 0,
            "auditCount": audit_count or 0,
            "usageTotal": float(usage_total or 0),
        },
    }


@router.get("/members", response_model=dict)
async def list_members(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(WorkspaceMember, User, Role, Department)
        .join(User, WorkspaceMember.user_id == User.id, isouter=True)
        .join(Role, WorkspaceMember.role_id == Role.id, isouter=True)
        .join(Department, WorkspaceMember.department_id == Department.id, isouter=True)
        .where(WorkspaceMember.workspace_id == workspace.id)
        .order_by(WorkspaceMember.joined_at.asc())
    )
    return {"success": True, "data": [_member_payload(member, account, role, dept) for member, account, role, dept in result.all()]}


@router.get("/members/{member_id}", response_model=dict)
async def get_member_detail(
    member_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    member, account, role, dept = await _get_member_row(db, workspace.id, member_id)
    return {"success": True, "data": _member_payload(member, account, role, dept)}


@router.patch("/members/{member_id}", response_model=dict)
async def update_member(
    member_id: str,
    payload: MemberUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    member, account, role, dept = await _get_member_row(db, workspace.id, member_id)
    if payload.role_code:
        next_role = await db.scalar(
            select(Role).where(Role.workspace_id == workspace.id, Role.code == payload.role_code)
        )
        if next_role is None:
            raise HTTPException(status_code=404, detail="角色不存在")
        member.role_id = next_role.id
        role = next_role
    if payload.department_id is not None:
        member.department_id = None if payload.department_id == "" else (await _get_department(db, workspace.id, payload.department_id)).id
        dept = None if member.department_id is None else await _get_department(db, workspace.id, str(member.department_id))
    if payload.status:
        member.status = payload.status
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="team.member.update",
            resource_type="member",
            resource_id=member.id,
            meta={"roleCode": payload.role_code, "departmentId": payload.department_id, "status": payload.status},
        )
    )
    await db.flush()
    return {"success": True, "data": _member_payload(member, account, role, dept)}


@router.post("/invitations", response_model=dict)
async def invite_member(
    payload: InviteMemberRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    await assert_member_quota(db, workspace)
    department_uuid = _uuid_or_400(payload.department_id, "department_id") if payload.department_id else None
    if department_uuid:
        exists = await db.scalar(select(Department.id).where(Department.id == department_uuid, Department.workspace_id == workspace.id))
        if not exists:
            raise HTTPException(status_code=404, detail="部门不存在")

    audit = AuditLog(
        workspace_id=workspace.id,
        user_id=user.id,
        action="team.invite",
        resource_type="workspace",
        resource_id=workspace.id,
        meta={"email": payload.email, "roleCode": payload.role_code, "departmentId": str(department_uuid) if department_uuid else None},
    )
    db.add(audit)
    await db.flush()
    return {
        "success": True,
        "data": {
            "id": str(audit.id),
            "email": payload.email,
            "status": "pending",
            "message": "邀请已记录，接入邮件或短信服务后可自动发送。",
        },
    }


@router.get("/departments", response_model=dict)
async def list_departments(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(Department).where(Department.workspace_id == workspace.id).order_by(Department.sort_order.asc(), Department.created_at.asc())
    )
    return {"success": True, "data": [_department_payload(item) for item in result.scalars().all()]}


@router.post("/departments", response_model=dict)
async def create_department(
    payload: DepartmentCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    parent_uuid = _uuid_or_400(payload.parent_id, "parent_id") if payload.parent_id else None
    item = Department(workspace_id=workspace.id, parent_id=parent_uuid, name=payload.name.strip())
    db.add(item)
    await db.flush()
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="team.department.create",
            resource_type="department",
            resource_id=item.id,
            meta={"name": item.name},
        )
    )
    return {"success": True, "data": _department_payload(item)}


@router.get("/departments/{department_id}", response_model=dict)
async def get_department_detail(
    department_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_department(db, workspace.id, department_id)
    member_count = await db.scalar(
        select(func.count(WorkspaceMember.id)).where(WorkspaceMember.department_id == item.id)
    )
    data = _department_payload(item)
    data["memberCount"] = int(member_count or 0)
    return {"success": True, "data": data}


@router.patch("/departments/{department_id}", response_model=dict)
async def update_department(
    department_id: str,
    payload: DepartmentUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_department(db, workspace.id, department_id)
    if payload.name is not None:
        item.name = payload.name.strip()
    if payload.parent_id is not None:
        parent_uuid = _uuid_or_400(payload.parent_id, "parent_id") if payload.parent_id else None
        if parent_uuid == item.id:
            raise HTTPException(status_code=400, detail="部门不能设置为自己的上级")
        item.parent_id = parent_uuid
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="team.department.update",
            resource_type="department",
            resource_id=item.id,
            meta={"name": item.name},
        )
    )
    await db.flush()
    return {"success": True, "data": _department_payload(item)}


@router.delete("/departments/{department_id}", response_model=dict)
async def delete_department(
    department_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    item = await _get_department(db, workspace.id, department_id)
    members = await db.execute(select(WorkspaceMember).where(WorkspaceMember.department_id == item.id))
    for member in members.scalars().all():
        member.department_id = None
    await db.delete(item)
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="team.department.delete",
            resource_type="department",
            resource_id=item.id,
            meta={"name": item.name},
        )
    )
    return {"success": True}


@router.get("/roles", response_model=dict)
async def list_roles(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(select(Role).where(Role.workspace_id == workspace.id).order_by(Role.is_system.desc(), Role.name.asc()))
    roles = []
    for role in result.scalars().all():
        permissions_result = await db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
            .order_by(Permission.module.asc(), Permission.code.asc())
        )
        roles.append(
            {
                "id": str(role.id),
                "name": role.name,
                "code": role.code,
                "description": role.description,
                "isSystem": role.is_system,
                "permissions": [
                    {
                        "id": str(permission.id),
                        "code": permission.code,
                        "name": permission.name,
                        "module": permission.module,
                    }
                    for permission in permissions_result.scalars().all()
                ],
            }
        )
    return {"success": True, "data": roles}


async def _replace_role_permissions(
    db: AsyncSession,
    role: Role,
    permission_codes: list[str] | None,
) -> None:
    if permission_codes is None:
        return
    codes = [code.strip() for code in permission_codes if code.strip()]
    permissions = []
    if codes:
        result = await db.execute(select(Permission).where(Permission.code.in_(codes)))
        permissions = result.scalars().all()
        found_codes = {item.code for item in permissions}
        missing = sorted(set(codes) - found_codes)
        if missing:
            raise HTTPException(status_code=404, detail=f"权限不存在：{', '.join(missing)}")
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    for permission in permissions:
        db.add(RolePermission(role_id=role.id, permission_id=permission.id))


@router.post("/roles", response_model=dict)
async def create_role(
    payload: RoleCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    exists = await db.scalar(select(Role.id).where(Role.workspace_id == workspace.id, Role.code == payload.code))
    if exists:
        raise HTTPException(status_code=409, detail="角色编码已存在")
    role = Role(
        workspace_id=workspace.id,
        name=payload.name.strip(),
        code=payload.code.strip(),
        description=payload.description.strip() if payload.description else None,
        is_system=False,
    )
    db.add(role)
    await db.flush()
    await _replace_role_permissions(db, role, payload.permission_codes)
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="team.role.create",
            resource_type="role",
            resource_id=role.id,
            meta={"name": role.name, "code": role.code},
        )
    )
    await db.flush()
    return await get_role_detail(str(role.id), user=user, db=db)


@router.get("/permissions", response_model=dict)
async def list_permissions(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Permission).order_by(Permission.module.asc(), Permission.code.asc()))
    return {
        "success": True,
        "data": [
            {
                "id": str(permission.id),
                "code": permission.code,
                "name": permission.name,
                "module": permission.module,
                "description": permission.description,
            }
            for permission in result.scalars().all()
        ],
    }


@router.get("/roles/{role_id}", response_model=dict)
async def get_role_detail(
    role_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    role = await _get_role(db, workspace.id, role_id)
    permissions_result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
        .order_by(Permission.module.asc(), Permission.code.asc())
    )
    return {
        "success": True,
        "data": {
            "id": str(role.id),
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "isSystem": role.is_system,
            "permissions": [
                {
                    "id": str(permission.id),
                    "code": permission.code,
                    "name": permission.name,
                    "module": permission.module,
                }
                for permission in permissions_result.scalars().all()
            ],
        },
    }


@router.patch("/roles/{role_id}", response_model=dict)
async def update_role(
    role_id: str,
    payload: RoleUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    role = await _get_role(db, workspace.id, role_id)
    if payload.name is not None and not role.is_system:
        role.name = payload.name.strip()
    if payload.description is not None:
        role.description = payload.description.strip()
    await _replace_role_permissions(db, role, payload.permission_codes)
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="team.role.update",
            resource_type="role",
            resource_id=role.id,
            meta={"name": role.name},
        )
    )
    await db.flush()
    return await get_role_detail(role_id, user=user, db=db)


@router.delete("/roles/{role_id}", response_model=dict)
async def delete_role(
    role_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    role = await _get_role(db, workspace.id, role_id)
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统角色不能删除")
    members = await db.execute(select(WorkspaceMember).where(WorkspaceMember.role_id == role.id))
    for member in members.scalars().all():
        member.role_id = None
    await db.delete(role)
    db.add(
        AuditLog(
            workspace_id=workspace.id,
            user_id=user.id,
            action="team.role.delete",
            resource_type="role",
            resource_id=role.id,
            meta={"name": role.name, "code": role.code},
        )
    )
    return {"success": True}


@router.get("/audit-logs", response_model=dict)
async def list_audit_logs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(AuditLog).where(AuditLog.workspace_id == workspace.id).order_by(AuditLog.created_at.desc()).limit(100)
    )
    return {
        "success": True,
        "data": [
            {
                "id": str(item.id),
                "action": item.action,
                "resourceType": item.resource_type,
                "resourceId": str(item.resource_id) if item.resource_id else None,
                "metadata": item.meta or {},
                "createdAt": _dt(item.created_at),
            }
            for item in result.scalars().all()
        ],
    }


@router.get("/usage", response_model=dict)
async def team_usage(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)
    result = await db.execute(
        select(UsageRecord.usage_type, UsageRecord.unit, func.coalesce(func.sum(UsageRecord.quantity), Decimal("0")))
        .where(UsageRecord.workspace_id == workspace.id)
        .group_by(UsageRecord.usage_type, UsageRecord.unit)
        .order_by(UsageRecord.usage_type.asc())
    )
    return {
        "success": True,
        "data": [
            {"usageType": usage_type, "unit": unit, "quantity": float(quantity or 0)}
            for usage_type, unit, quantity in result.all()
        ],
    }


# ── 团队共享文件夹 ────────────────────────────

class SharedFolderPayload(BaseModel):
    folder_id: str
    name: str
    file_count: int = 0
    shared_by_name: str | None = None
    created_at: str | None = None


@router.get("/shared-folders", response_model=dict)
async def list_shared_folders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)

    from app.models.drive import Folder
    from app.models.drive import WorkspaceFile as WFile

    stmt = (
        select(Folder)
        .where(
            Folder.workspace_id == workspace.id,
            Folder.is_team_shared == True,
            Folder.deleted_at.is_(None),
        )
        .order_by(Folder.created_at.desc())
    )
    result = await db.execute(stmt)
    folders = result.scalars().all()

    data = []
    for folder in folders:
        file_count = await db.scalar(
            select(func.count(WFile.id)).where(
                WFile.folder_id == folder.id,
                WFile.deleted_at.is_(None),
            )
        )
        data.append(SharedFolderPayload(
            folder_id=str(folder.id),
            name=folder.name,
            file_count=int(file_count or 0),
            shared_by_name=None,
            created_at=folder.created_at.isoformat() if folder.created_at else None,
        ))

    return {"success": True, "data": [d.model_dump() for d in data]}


@router.post("/shared-folders/{folder_id}", response_model=dict)
async def toggle_shared_folder(
    folder_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    workspace = await ensure_user_workspace(db, user)

    from app.models.drive import Folder

    stmt = select(Folder).where(
        Folder.id == folder_id,
        Folder.workspace_id == workspace.id,
        Folder.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    folder.is_team_shared = not folder.is_team_shared
    folder.shared_by = user.id if folder.is_team_shared else None

    db.add(AuditLog(
        workspace_id=workspace.id,
        user_id=user.id,
        action="folder.share_toggle",
        resource_type="folder",
        resource_id=folder_id,
        meta={"is_team_shared": folder.is_team_shared},
    ))

    return {"success": True, "is_team_shared": folder.is_team_shared}
