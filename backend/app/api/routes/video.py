from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/video", tags=["video"])

GENERATION_TO_DB = {
    "text": "text_to_video",
    "image": "image_to_video",
    "video": "video_reference",
    "storyboard": "storyboard",
}
DB_TO_GENERATION = {value: key for key, value in GENERATION_TO_DB.items()}

STATUS_TO_UI = {
    "pending": "generating",
    "processing": "generating",
    "succeeded": "success",
    "failed": "failed",
    "cancelled": "failed",
}
MODEL_STATUS_TO_UI = {
    "available": "available",
    "coming_soon": "coming",
    "maintenance": "maintenance",
    "disabled": "maintenance",
}
INPUT_TYPE_LABELS = {
    "text": "文本",
    "image": "图片",
    "video": "视频",
    "audio": "音频",
    "script": "脚本",
}
OUTPUT_TYPE_LABELS = {
    "video": "视频",
    "audio": "音频",
    "image": "图片",
}
REFERENCE_STRENGTH_TO_UI = {"low": "低", "medium": "中", "high": "高"}
REFERENCE_STRENGTH_TO_DB = {value: key for key, value in REFERENCE_STRENGTH_TO_UI.items()}
THUMBNAIL_TONES = ["blue", "cyan", "violet", "emerald", "rose"]


class VideoTaskCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    model_id: str = Field(alias="modelId")
    generation_type: str = Field(default="text", alias="generationType")
    prompt: str = ""
    negative_prompt: str = Field(default="", alias="negativePrompt")
    action_description: str = Field(default="", alias="actionDescription")
    storyboard_text: str = Field(default="", alias="storyboardText")
    input_image_url: str | None = Field(default=None, alias="inputImageUrl")
    input_video_url: str | None = Field(default=None, alias="inputVideoUrl")
    aspect_ratio: str = Field(default="16:9", alias="aspectRatio")
    duration: str | int = "10 秒"
    resolution: str = "1080p"
    style: str = "电影感"
    camera_motion: str = Field(default="推近", alias="cameraMotion")
    reference_strength: str = Field(default="中", alias="referenceStrength")
    count: str | int = "1 条"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, list) else []
        except json.JSONDecodeError:
            return []
    return list(value) if isinstance(value, tuple) else []


def _label_list(values: Any, labels: dict[str, str]) -> list[str]:
    return [labels.get(str(item), str(item)) for item in _as_list(values)]


def _duration_label(value: Any) -> str:
    if value is None:
        return "10 秒"
    try:
        return f"{int(value)} 秒"
    except (TypeError, ValueError):
        return str(value)


def _duration_seconds(value: str | int | None) -> int:
    if value is None:
        return 10
    if isinstance(value, int):
        return value
    match = re.search(r"\d+", value)
    if match:
        return int(match.group())
    return 60


def _count_value(value: str | int | None) -> int:
    if value is None:
        return 1
    if isinstance(value, int):
        return max(value, 1)
    match = re.search(r"\d+", value)
    return max(int(match.group()), 1) if match else 1


def _summary(prompt: str | None) -> str:
    text_value = re.sub(r"\s+", " ", (prompt or "").strip())
    if len(text_value) <= 34:
        return text_value or "未填写提示词"
    return f"{text_value[:34]}..."


def _relative_time(value: datetime | None) -> str:
    if not value:
        return "-"
    now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
    if value.date() == now.date():
        return f"今天 {value:%H:%M}"
    if value.date() == (now - timedelta(days=1)).date():
        return f"昨天 {value:%H:%M}"
    return f"{value.month} 月 {value.day} 日 {value:%H:%M}"


def _thumbnail_tone(identifier: str) -> str:
    return THUMBNAIL_TONES[sum(identifier.encode("utf-8")) % len(THUMBNAIL_TONES)]


def _generation_types(value: Any) -> list[str]:
    return [DB_TO_GENERATION.get(str(item), str(item)) for item in _as_list(value)]


def _model_filters(row: dict[str, Any], supported_types: list[str]) -> list[str]:
    filters: list[str] = []
    if row.get("is_recommended"):
        filters.append("recommended")
    filters.append("chinese" if row.get("provider_country") == "CN" else "global")
    if row.get("is_open_source"):
        filters.append("open")
    if "text" in supported_types:
        filters.append("text")
    if "image" in supported_types:
        filters.append("image")

    text_blob = " ".join(
        [
            row.get("display_name") or "",
            row.get("short_description") or "",
            row.get("description") or "",
            " ".join(str(item) for item in _as_list(row.get("tags"))),
            " ".join(str(item) for item in _as_list(row.get("use_cases"))),
        ]
    )
    if any(keyword in text_blob for keyword in ["人物", "口播", "角色"]):
        filters.append("people")
    if any(keyword in text_blob for keyword in ["商业", "广告", "产品", "品牌"]):
        filters.append("commercial")
    return list(dict.fromkeys(filters))


def _model_payload(row: dict[str, Any]) -> dict[str, Any]:
    supported_types = _generation_types(row.get("supported_generation_types"))
    supported_durations = [_duration_label(value) for value in _as_list(row.get("supported_durations"))]
    supported_reference_strengths = [
        REFERENCE_STRENGTH_TO_UI.get(str(value), str(value)) for value in _as_list(row.get("supported_reference_strengths"))
    ]
    max_generation_count = int(row.get("max_generation_count") or 1)
    pending_parameters: dict[str, list[str]] = {}
    if not row.get("supports_long_video"):
        pending_parameters["durations"] = ["更长"]
    if not row.get("supports_4k"):
        pending_parameters["resolutions"] = ["4K"]
    pending_counts = [f"{count} 条" for count in (1, 2, 4) if count > max_generation_count]
    if pending_counts:
        pending_parameters["generationCounts"] = pending_counts

    filters = _model_filters(row, supported_types)
    category = "commercial" if "commercial" in filters else "chinese" if "chinese" in filters else "open" if "open" in filters else "global"
    max_duration = row.get("max_duration_seconds")
    parameter_limits = [
        f"最多生成 {max_generation_count} 条",
        f"最长 {_duration_label(max_duration)}" if max_duration else "按模型默认时长生成",
    ]
    if row.get("supports_4k"):
        parameter_limits.append("支持 4K 输出")
    if row.get("supports_audio"):
        parameter_limits.append("支持音频或音画同步")

    return {
        "id": str(row["id"]),
        "name": row.get("name") or "",
        "provider": row.get("provider_name") or "-",
        "version": row.get("version") or "-",
        "displayName": row.get("display_name") or row.get("name") or "",
        "description": row.get("short_description") or row.get("description") or "",
        "position": row.get("short_description") or "视频生成模型",
        "tags": _as_list(row.get("tags")),
        "category": category,
        "filters": filters,
        "capabilities": supported_types,
        "supportedGenerationTypes": supported_types,
        "useCases": _as_list(row.get("use_cases")),
        "inputTypes": _label_list(row.get("input_types"), INPUT_TYPE_LABELS),
        "outputTypes": _label_list(row.get("output_types"), OUTPUT_TYPE_LABELS),
        "supportedAspectRatios": _as_list(row.get("supported_aspect_ratios")) or ["16:9"],
        "supportedDurations": supported_durations or ["10 秒"],
        "supportedResolutions": _as_list(row.get("supported_resolutions")) or ["1080p"],
        "supportedStyles": _as_list(row.get("supported_styles")) or ["写实"],
        "supportedCameraMotions": _as_list(row.get("supported_camera_motions")) or ["固定镜头"],
        "supportedReferenceStrengths": supported_reference_strengths,
        "maxGenerationCount": max_generation_count,
        "supportsLongVideo": bool(row.get("supports_long_video")),
        "supports4k": bool(row.get("supports_4k")),
        "supportsAudio": bool(row.get("supports_audio")),
        "supportsImageToVideo": bool(row.get("supports_image_to_video")),
        "supportsVideoReference": bool(row.get("supports_video_reference")),
        "supportsStoryboard": bool(row.get("supports_storyboard")),
        "pendingParameters": pending_parameters,
        "status": MODEL_STATUS_TO_UI.get(row.get("status") or "available", "maintenance"),
        "isRecommended": bool(row.get("is_recommended")),
        "sortOrder": int(row.get("sort_order") or 0),
        "parameterLimits": parameter_limits,
        "createdAt": row.get("created_at").isoformat() if row.get("created_at") else "",
        "updatedAt": row.get("updated_at").isoformat() if row.get("updated_at") else "",
    }


MODEL_QUERY = """
SELECT
    m.id,
    m.name,
    m.version,
    m.display_name,
    m.short_description,
    m.description,
    m.model_code,
    m.status,
    m.is_recommended,
    m.is_featured,
    m.is_open_source,
    m.input_types,
    m.output_types,
    m.tags,
    m.use_cases,
    m.sort_order,
    m.created_at,
    m.updated_at,
    p.display_name AS provider_name,
    p.country AS provider_country,
    params.supported_generation_types,
    params.supported_aspect_ratios,
    params.supported_durations,
    params.supported_resolutions,
    params.supported_styles,
    params.supported_camera_motions,
    params.supported_reference_strengths,
    params.max_generation_count,
    params.max_duration_seconds,
    params.supports_long_video,
    params.supports_4k,
    params.supports_audio,
    params.supports_image_to_video,
    params.supports_video_reference,
    params.supports_storyboard
FROM video_models m
LEFT JOIN video_model_providers p ON p.id = m.provider_id
LEFT JOIN video_model_parameters params ON params.model_id = m.id
WHERE m.deleted_at IS NULL
"""


async def _model_by_identifier(db: AsyncSession, identifier: str) -> dict[str, Any] | None:
    result = await db.execute(
        text(
            MODEL_QUERY
            + """
              AND (m.id::text = :identifier OR m.model_code = :identifier)
              ORDER BY m.sort_order, m.display_name
              LIMIT 1
              """
        ),
        {"identifier": identifier},
    )
    row = result.mappings().first()
    return dict(row) if row else None


@router.get("/models", response_model=dict)
async def list_video_models(
    search: str | None = Query(default=None),
    recommended_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_session),
):
    params: dict[str, Any] = {}
    clauses: list[str] = []
    if recommended_only:
        clauses.append("m.is_recommended = TRUE")
    if search:
        params["search"] = f"%{search.strip()}%"
        clauses.append("(m.display_name ILIKE :search OR m.short_description ILIKE :search OR m.description ILIKE :search)")

    where_sql = f" AND {' AND '.join(clauses)}" if clauses else ""
    result = await db.execute(text(MODEL_QUERY + where_sql + " ORDER BY m.sort_order, m.display_name"), params)
    items = [_model_payload(dict(row)) for row in result.mappings().all()]
    return {"success": True, "data": {"items": items, "total": len(items)}}


@router.get("/models/{model_id}", response_model=dict)
async def get_video_model(model_id: str, db: AsyncSession = Depends(get_session)):
    row = await _model_by_identifier(db, model_id)
    if not row:
        raise HTTPException(status_code=404, detail="视频模型不存在")
    return {"success": True, "data": _model_payload(row)}


TASK_QUERY = """
SELECT
    t.id,
    t.user_id,
    t.model_id,
    t.generation_type,
    t.prompt,
    t.negative_prompt,
    t.storyboard_text,
    t.aspect_ratio,
    t.duration,
    t.resolution,
    t.style,
    t.camera_motion,
    t.reference_strength,
    t.generation_count,
    t.status,
    t.progress,
    t.error_message,
    t.created_at,
    t.updated_at,
    m.display_name AS model_name,
    result.video_url,
    result.thumbnail_url,
    result.cover_url,
    COALESCE(result.is_saved_to_cloud, FALSE) AS is_saved
FROM video_generation_tasks t
LEFT JOIN video_models m ON m.id = t.model_id
LEFT JOIN LATERAL (
    SELECT video_url, thumbnail_url, cover_url, is_saved_to_cloud
    FROM video_generation_results
    WHERE task_id = t.id AND status != 'deleted'
    ORDER BY result_index ASC, created_at ASC
    LIMIT 1
) result ON TRUE
WHERE t.deleted_at IS NULL
"""


def _task_payload(row: dict[str, Any]) -> dict[str, Any]:
    identifier = str(row["id"])
    saved = bool(row.get("is_saved"))
    base_status = STATUS_TO_UI.get(row.get("status") or "pending", "generating")
    status = "saved" if saved and base_status == "success" else base_status
    prompt = row.get("prompt") or ""
    return {
        "id": identifier,
        "userId": str(row.get("user_id") or ""),
        "modelId": str(row.get("model_id") or ""),
        "modelName": row.get("model_name") or "未知模型",
        "generationType": DB_TO_GENERATION.get(row.get("generation_type") or "text_to_video", "text"),
        "prompt": prompt,
        "negativePrompt": row.get("negative_prompt") or "",
        "promptSummary": _summary(prompt),
        "inputImageUrl": None,
        "inputVideoUrl": None,
        "storyboardText": row.get("storyboard_text") or "",
        "aspectRatio": row.get("aspect_ratio") or "16:9",
        "duration": _duration_label(row.get("duration")),
        "resolution": row.get("resolution") or "1080p",
        "style": row.get("style") or "写实",
        "cameraMotion": row.get("camera_motion") or "固定镜头",
        "referenceStrength": REFERENCE_STRENGTH_TO_UI.get(row.get("reference_strength") or "medium", "中"),
        "count": f"{int(row.get('generation_count') or 1)} 条",
        "status": status,
        "progress": int(row.get("progress") or 0),
        "resultVideoUrl": row.get("video_url"),
        "thumbnailUrl": row.get("thumbnail_url") or row.get("cover_url"),
        "thumbnailTone": _thumbnail_tone(identifier),
        "errorMessage": row.get("error_message"),
        "isSaved": saved,
        "createdAt": row.get("created_at").isoformat() if row.get("created_at") else "",
        "createdAtLabel": _relative_time(row.get("created_at")),
        "updatedAt": row.get("updated_at").isoformat() if row.get("updated_at") else "",
    }


async def _task_by_id(db: AsyncSession, task_id: str, user_id: str) -> dict[str, Any] | None:
    result = await db.execute(
        text(TASK_QUERY + " AND t.user_id = :user_id AND t.id::text = :task_id LIMIT 1"),
        {"user_id": user_id, "task_id": task_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


@router.get("/tasks", response_model=dict)
async def list_video_tasks(
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    params: dict[str, Any] = {"user_id": str(user.id), "limit": limit}
    clauses = ["t.user_id = :user_id"]
    if status and status != "all":
        db_statuses = {
            "generating": ("pending", "processing"),
            "success": ("succeeded",),
            "failed": ("failed", "cancelled"),
            "saved": ("succeeded",),
        }.get(status, (status,))
        status_placeholders = []
        for index, db_status in enumerate(db_statuses):
            key = f"status_{index}"
            params[key] = db_status
            status_placeholders.append(f":{key}")
        clauses.append(f"t.status IN ({', '.join(status_placeholders)})")
        if status == "saved":
            clauses.append("COALESCE(result.is_saved_to_cloud, FALSE) = TRUE")
    if search:
        params["search"] = f"%{search.strip()}%"
        clauses.append("(t.prompt ILIKE :search OR m.display_name ILIKE :search)")

    result = await db.execute(
        text(TASK_QUERY + f" AND {' AND '.join(clauses)} ORDER BY t.created_at DESC LIMIT :limit"),
        params,
    )
    items = [_task_payload(dict(row)) for row in result.mappings().all()]
    return {"success": True, "data": {"items": items, "total": len(items)}}


@router.get("/tasks/recent", response_model=dict)
async def recent_video_tasks(
    limit: int = Query(default=3, ge=1, le=10),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        text(TASK_QUERY + " AND t.user_id = :user_id ORDER BY t.created_at DESC LIMIT :limit"),
        {"user_id": str(user.id), "limit": limit},
    )
    return {"success": True, "data": [_task_payload(dict(row)) for row in result.mappings().all()]}


@router.get("/tasks/{task_id}", response_model=dict)
async def get_video_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await _task_by_id(db, task_id, str(user.id))
    if not row:
        raise HTTPException(status_code=404, detail="视频任务不存在")
    return {"success": True, "data": _task_payload(row)}


@router.post("/tasks", response_model=dict)
async def create_video_task(
    payload: VideoTaskCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    model_row = await _model_by_identifier(db, payload.model_id)
    if not model_row:
        raise HTTPException(status_code=404, detail="视频模型不存在")
    if model_row.get("status") != "available":
        raise HTTPException(status_code=400, detail="当前模型暂不可用")

    generation_type = GENERATION_TO_DB.get(payload.generation_type, payload.generation_type)
    supported_types = _as_list(model_row.get("supported_generation_types"))
    if supported_types and generation_type not in supported_types:
        raise HTTPException(status_code=400, detail="当前模型不支持该生成方式")

    prompt = (payload.storyboard_text if payload.generation_type == "storyboard" and payload.storyboard_text else payload.prompt).strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="请先填写提示词")

    should_fail = bool(re.search(r"失败|繁忙|不支持|错误|违规", prompt))
    status = "failed" if should_fail else "succeeded"
    progress = 42 if should_fail else 100
    error_message = "模型繁忙，建议稍后重试或切换模型。" if should_fail else None
    generation_count = min(_count_value(payload.count), int(model_row.get("max_generation_count") or 1))
    duration_seconds = _duration_seconds(payload.duration)
    request_payload = payload.model_dump(by_alias=True)

    insert_result = await db.execute(
        text(
            """
            INSERT INTO video_generation_tasks (
                user_id, model_id, generation_type, prompt, negative_prompt, storyboard_text,
                aspect_ratio, duration, resolution, style, camera_motion, reference_strength,
                generation_count, status, progress, error_code, error_message, request_payload,
                response_payload, started_at, completed_at
            )
            VALUES (
                :user_id, :model_id, :generation_type, :prompt, :negative_prompt, :storyboard_text,
                :aspect_ratio, :duration, :resolution, :style, :camera_motion, :reference_strength,
                :generation_count, :status, :progress, :error_code, :error_message,
                CAST(:request_payload AS jsonb), CAST(:response_payload AS jsonb), NOW(), NOW()
            )
            RETURNING id
            """
        ),
        {
            "user_id": str(user.id),
            "model_id": str(model_row["id"]),
            "generation_type": generation_type,
            "prompt": prompt,
            "negative_prompt": payload.negative_prompt.strip(),
            "storyboard_text": payload.storyboard_text.strip() if payload.generation_type == "storyboard" else None,
            "aspect_ratio": payload.aspect_ratio,
            "duration": duration_seconds,
            "resolution": payload.resolution,
            "style": payload.style,
            "camera_motion": payload.camera_motion,
            "reference_strength": REFERENCE_STRENGTH_TO_DB.get(payload.reference_strength, payload.reference_strength),
            "generation_count": generation_count,
            "status": status,
            "progress": progress,
            "error_code": "model_busy" if should_fail else None,
            "error_message": error_message,
            "request_payload": json.dumps(request_payload, ensure_ascii=False),
            "response_payload": json.dumps({"local_preview": True, "status": status}, ensure_ascii=False),
        },
    )
    task_id = str(insert_result.scalar_one())

    if payload.input_image_url or payload.input_video_url:
        await db.execute(
            text(
                """
                INSERT INTO video_generation_assets (
                    task_id, user_id, asset_type, original_filename, file_url, metadata
                )
                VALUES (:task_id, :user_id, :asset_type, :original_filename, :file_url, CAST(:metadata AS jsonb))
                """
            ),
            {
                "task_id": task_id,
                "user_id": str(user.id),
                "asset_type": "image" if payload.input_image_url else "video",
                "original_filename": "参考素材",
                "file_url": payload.input_image_url or payload.input_video_url,
                "metadata": json.dumps({"source": "video_create_page"}, ensure_ascii=False),
            },
        )

    if not should_fail:
        for index in range(1, generation_count + 1):
            await db.execute(
                text(
                    """
                    INSERT INTO video_generation_results (
                        task_id, user_id, result_index, video_url, thumbnail_url, cover_url,
                        duration, aspect_ratio, resolution, status
                    )
                    VALUES (
                        :task_id, :user_id, :result_index, :video_url, :thumbnail_url, :cover_url,
                        :duration, :aspect_ratio, :resolution, 'available'
                    )
                    """
                ),
                {
                    "task_id": task_id,
                    "user_id": str(user.id),
                    "result_index": index,
                    "video_url": f"https://storage.xuguang.local/video-preview/{task_id}-{index}.mp4",
                    "thumbnail_url": None,
                    "cover_url": None,
                    "duration": duration_seconds,
                    "aspect_ratio": payload.aspect_ratio,
                    "resolution": payload.resolution,
                },
            )

    await db.execute(
        text(
            """
            INSERT INTO video_generation_events (task_id, event_type, message, payload)
            VALUES (:task_id, :event_type, :message, CAST(:payload AS jsonb))
            """
        ),
        {
            "task_id": task_id,
            "event_type": status,
            "message": "视频生成失败" if should_fail else "视频生成完成",
            "payload": json.dumps({"progress": progress}, ensure_ascii=False),
        },
    )
    await db.flush()

    row = await _task_by_id(db, task_id, str(user.id))
    return {"success": True, "data": _task_payload(row or {})}


@router.post("/tasks/{task_id}/save", response_model=dict)
async def save_video_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await _task_by_id(db, task_id, str(user.id))
    if not row:
        raise HTTPException(status_code=404, detail="视频任务不存在")
    if row.get("status") != "succeeded":
        raise HTTPException(status_code=400, detail="只有生成成功的视频可以保存")

    await db.execute(
        text(
            """
            UPDATE video_generation_results
            SET is_saved_to_cloud = TRUE
            WHERE task_id::text = :task_id AND user_id = :user_id AND status != 'deleted'
            """
        ),
        {"task_id": task_id, "user_id": str(user.id)},
    )
    await db.execute(
        text(
            """
            INSERT INTO video_generation_events (task_id, event_type, message, payload)
            VALUES (:task_id, 'saved_to_cloud', '已保存到云盘', '{}'::jsonb)
            """
        ),
        {"task_id": task_id},
    )
    await db.flush()
    updated = await _task_by_id(db, task_id, str(user.id))
    return {"success": True, "data": _task_payload(updated or {})}


@router.post("/tasks/{task_id}/cancel", response_model=dict)
async def cancel_video_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await _task_by_id(db, task_id, str(user.id))
    if not row:
        raise HTTPException(status_code=404, detail="视频任务不存在")
    await db.execute(
        text(
            """
            UPDATE video_generation_tasks
            SET status = 'cancelled', progress = 0, error_message = '用户取消生成'
            WHERE id::text = :task_id AND user_id = :user_id AND status IN ('pending', 'processing')
            """
        ),
        {"task_id": task_id, "user_id": str(user.id)},
    )
    await db.flush()
    updated = await _task_by_id(db, task_id, str(user.id))
    return {"success": True, "data": _task_payload(updated or row)}


@router.delete("/tasks/{task_id}", response_model=dict)
async def delete_video_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await _task_by_id(db, task_id, str(user.id))
    if not row:
        raise HTTPException(status_code=404, detail="视频任务不存在")
    await db.execute(
        text(
            """
            UPDATE video_generation_tasks
            SET deleted_at = NOW()
            WHERE id::text = :task_id AND user_id = :user_id
            """
        ),
        {"task_id": task_id, "user_id": str(user.id)},
    )
    return {"success": True}
