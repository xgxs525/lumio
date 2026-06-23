from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Plan
from app.models.drive import Folder
from app.models.user import User
from app.models.workspace import Permission, Role, RolePermission, Workspace, WorkspaceMember
from app.services.billing import ensure_billing_catalog

DEFAULT_USER_EMAIL = 'guangyiiiiiwei@qq.com'
DEFAULT_WORKSPACE_SLUG = 'lumio-default'

PERMISSIONS = [
    ('workspace.view', '查看工作区', 'workspace'),
    ('drive.manage', '管理云盘', 'drive'),
    ('docs.manage', '管理文档', 'docs'),
    ('knowledge.manage', '管理知识库', 'knowledge'),
    ('ai.use', '使用 AI 能力', 'ai'),
    ('billing.manage', '管理会员和订单', 'billing'),
]

PLANS = [
    ('free', '免费版', '适合个人体验和小文件处理', Decimal('0'), 10 * 1024 * 1024 * 1024, 100000),
    ('pro', '专业版', '适合个人办公和小团队', Decimal('29'), 100 * 1024 * 1024 * 1024, 1000000),
    ('team', '团队版', '支持多人协作、共享空间和权限管理', Decimal('99'), 1024 * 1024 * 1024 * 1024, 5000000),
    ('enterprise', '企业版', '支持私有化部署、API 接入和专属服务', Decimal('0'), 0, 0),
]

ROOT_FOLDERS = [
    ('处理结果', 'system_results'),
    ('团队共享资料', 'team_shared'),
    ('模板资料库', 'templates'),
    ('知识库附件', 'knowledge_assets'),
]


async def ensure_default_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == DEFAULT_USER_EMAIL))
    user = result.scalar_one_or_none()
    if user:
        return user

    result = await db.execute(select(User).order_by(User.created_at.asc()).limit(1))
    user = result.scalar_one_or_none()
    if user:
        if not user.name:
            user.name = user.nickname or '序光运营号'
        if not user.password_hash:
            user.password_hash = user.hashed_password or ''
        return user

    user = User(
        email=DEFAULT_USER_EMAIL,
        name='序光运营号',
        nickname='序光运营号',
        password_hash='',
        hashed_password='',
        locale='zh-CN',
        timezone='Asia/Shanghai',
    )
    db.add(user)
    await db.flush()
    return user


async def ensure_permissions(db: AsyncSession) -> dict[str, Permission]:
    existing = await db.execute(select(Permission).where(Permission.code.in_([code for code, _, _ in PERMISSIONS])))
    by_code = {item.code: item for item in existing.scalars().all()}
    for code, name, module in PERMISSIONS:
        if code not in by_code:
            item = Permission(code=code, name=name, module=module, description='')
            db.add(item)
            by_code[code] = item
    await db.flush()
    return by_code


async def ensure_plans(db: AsyncSession) -> None:
    await ensure_billing_catalog(db)


async def ensure_default_workspace(db: AsyncSession) -> tuple[User, Workspace]:
    user = await ensure_default_user(db)
    await ensure_plans(db)
    permissions = await ensure_permissions(db)

    result = await db.execute(select(Workspace).where(Workspace.slug == DEFAULT_WORKSPACE_SLUG))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        workspace = Workspace(
            name='序光默认工作区',
            slug=DEFAULT_WORKSPACE_SLUG,
            owner_id=user.id,
            plan='free',
            locale='zh-CN',
            timezone='Asia/Shanghai',
        )
        db.add(workspace)
        await db.flush()

    result = await db.execute(
        select(Role).where(Role.workspace_id == workspace.id, Role.code == 'owner')
    )
    owner_role = result.scalar_one_or_none()
    if owner_role is None:
        owner_role = Role(
            workspace_id=workspace.id,
            name='所有者',
            code='owner',
            description='拥有当前工作区的全部管理权限',
            is_system=True,
        )
        db.add(owner_role)
        await db.flush()

    for permission in permissions.values():
        result = await db.execute(
            select(RolePermission).where(
                RolePermission.role_id == owner_role.id,
                RolePermission.permission_id == permission.id,
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(RolePermission(role_id=owner_role.id, permission_id=permission.id))

    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        db.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role_id=owner_role.id,
                status='active',
            )
        )

    for folder_name, folder_code in ROOT_FOLDERS:
        result = await db.execute(
            select(Folder).where(
                Folder.workspace_id == workspace.id,
                Folder.parent_id.is_(None),
                Folder.name == folder_name,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            db.add(
                Folder(
                    workspace_id=workspace.id,
                    owner_id=user.id,
                    name=folder_name,
                    parent_id=None,
                )
            )
        elif existing.deleted_at is not None:
            existing.deleted_at = None

    await db.flush()
    return user, workspace


async def ensure_user_workspace(db: AsyncSession, user: User) -> Workspace:
    await ensure_plans(db)
    permissions = await ensure_permissions(db)
    slug = f'user-{user.id.hex[:12]}'

    result = await db.execute(select(Workspace).where(Workspace.slug == slug))
    workspace = result.scalar_one_or_none()
    if workspace is None:
        display_name = user.name or user.nickname or '我的'
        workspace = Workspace(
            name=f'{display_name}的工作区',
            slug=slug,
            owner_id=user.id,
            plan='free',
            locale=user.locale or 'zh-CN',
            timezone=user.timezone or 'Asia/Shanghai',
        )
        db.add(workspace)
        await db.flush()

    result = await db.execute(
        select(Role).where(Role.workspace_id == workspace.id, Role.code == 'owner')
    )
    owner_role = result.scalar_one_or_none()
    if owner_role is None:
        owner_role = Role(
            workspace_id=workspace.id,
            name='所有者',
            code='owner',
            description='拥有当前工作区的全部管理权限',
            is_system=True,
        )
        db.add(owner_role)
        await db.flush()

    for permission in permissions.values():
        result = await db.execute(
            select(RolePermission).where(
                RolePermission.role_id == owner_role.id,
                RolePermission.permission_id == permission.id,
            )
        )
        if result.scalar_one_or_none() is None:
            db.add(RolePermission(role_id=owner_role.id, permission_id=permission.id))

    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        db.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=user.id,
                role_id=owner_role.id,
                status='active',
            )
        )

    for folder_name, _ in ROOT_FOLDERS:
        result = await db.execute(
            select(Folder).where(
                Folder.workspace_id == workspace.id,
                Folder.parent_id.is_(None),
                Folder.name == folder_name,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            db.add(
                Folder(
                    workspace_id=workspace.id,
                    owner_id=user.id,
                    name=folder_name,
                    parent_id=None,
                )
            )
        elif existing.deleted_at is not None:
            existing.deleted_at = None

    await db.flush()
    return workspace
