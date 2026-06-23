"""Seed model marketplace with 10 model versions."""

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal, engine
from app.models.model_registry import (
    ModelCapability,
    ModelDescription,
    ModelFamily,
    ModelPricing,
    ModelProvider,
    ModelVersion,
    ModelVersionCapability,
)


async def seed():
    async with engine.begin() as conn:
        # Ensure tables exist
        await conn.run_sync(lambda sync_conn: None)

    async with AsyncSessionLocal() as db:  # type: AsyncSession
        # ── Providers ────────────────────────────────────────
        providers = [
            ("openai", "OpenAI", "OpenAI", "https://openai.com", "Leading AI research company."),
            ("anthropic", "Anthropic", "Anthropic", "https://anthropic.com", "AI safety company behind Claude."),
            ("deepseek", "DeepSeek", "DeepSeek", "https://deepseek.com", "Chinese AI lab."),
            ("google", "Google", "Google", "https://ai.google", "Google AI / DeepMind."),
            ("zhipu", "智谱", "智谱 AI", "https://zhipuai.cn", "Chinese AI company behind GLM."),
            ("alibaba", "阿里", "阿里云", "https://aliyun.com", "Qwen model series."),
            ("moonshot", "月之暗面", "月之暗面", "https://moonshot.cn", "Creators of Kimi."),
        ]
        provider_map: dict[str, ModelProvider] = {}
        for code, name, display, website, desc in providers:
            p = ModelProvider(id=uuid.uuid4(), code=code, name=name, display_name=display, website_url=website, description=desc)
            db.add(p)
            provider_map[code] = p

        await db.flush()

        # ── Capabilities ─────────────────────────────────────
        caps_data = [
            ("text_chat", "文本对话", "普通对话能力", "text"),
            ("long_context", "长文本分析", "处理长文档和长上下文", "reasoning"),
            ("code_gen", "代码编程", "生成和解释代码", "code"),
            ("file_analysis", "文件理解", "读取和分析文件", "file"),
            ("image_understanding", "图像理解", "理解和描述图片", "image"),
            ("image_gen", "图像生成", "根据描述生成图片", "image"),
            ("writing", "写作创作", "写作、润色和翻译", "text"),
            ("reasoning", "逻辑推理", "复杂推理和分析", "reasoning"),
            ("search", "搜索增强", "结合搜索进行回答", "search"),
            ("multimodal", "多模态理解", "理解图文混合内容", "image"),
            ("video_gen", "视频创作", "生成视频脚本和方案", "video"),
            ("fast_reply", "快速回复", "低延迟快速响应", "text"),
        ]
        cap_map: dict[str, ModelCapability] = {}
        for code, name, desc, cat in caps_data:
            cap = ModelCapability(id=uuid.uuid4(), code=code, name=name, description=desc, category=cat)
            db.add(cap)
            cap_map[code] = cap
        await db.flush()

        # ── Families ─────────────────────────────────────────
        families_def = [
            ("gpt", "GPT", "GPT", provider_map["openai"]),
            ("claude", "Claude", "Claude", provider_map["anthropic"]),
            ("deepseek_v4", "DeepSeek-V4", "DeepSeek V4 系列", provider_map["deepseek"]),
            ("gemini", "Gemini", "Gemini", provider_map["google"]),
            ("glm", "GLM", "GLM", provider_map["zhipu"]),
            ("qwen", "Qwen", "Qwen", provider_map["alibaba"]),
            ("kimi", "Kimi", "Kimi", provider_map["moonshot"]),
        ]
        family_map: dict[str, ModelFamily] = {}
        for code, name, display, prov in families_def:
            f = ModelFamily(id=uuid.uuid4(), provider_id=prov.id, code=code, name=name, display_name=display)
            db.add(f)
            family_map[code] = f
        await db.flush()

        # ── Versions ─────────────────────────────────────────
        versions_def = [
            # (family_key, code, display_name, version_name, context_window, supports_files, supports_images, supports_video, quality_score, speed_score, cost_level, is_recommended)
            ("claude", "claude-sonnet-4.6", "Claude Sonnet 4.6", "Sonnet 4.6", 200000, True, True, False, 4.5, 3.0, 4, True),
            ("gpt", "gpt-5.6", "GPT-5.6", "5.6", 128000, True, True, False, 4.5, 3.0, 4, False),
            ("deepseek_v4", "deepseek-v4-pro", "DeepSeek-V4-Pro", "V4 Pro", 128000, True, False, False, 4.3, 2.8, 3, False),
            ("gemini", "gemini-1.0-ultra", "Gemini 1.0 Ultra", "1.0 Ultra", 1000000, True, True, False, 4.2, 3.0, 4, False),
            ("deepseek_v4", "deepseek-v4-flash", "DeepSeek-V4-Flash", "V4 Flash", 32000, False, False, False, 3.0, 4.5, 1, False),
            ("gpt", "gpt-5.5", "GPT-5.5", "5.5", 64000, True, True, False, 4.0, 4.0, 3, False),
            ("claude", "claude-sonnet-4.5", "Claude Sonnet 4.5", "Sonnet 4.5", 200000, True, True, False, 4.0, 3.0, 3, False),
            ("glm", "glm-5.2", "GLM-5.2", "5.2", 128000, True, True, False, 4.0, 3.0, 3, False),
            ("qwen", "qwen3.7-max", "Qwen3.7-Max", "3.7 Max", 131072, True, False, False, 4.0, 3.0, 3, False),
            ("kimi", "kimi-k2.7-code", "Kimi K2.7 Code", "K2.7 Code", 256000, True, False, False, 4.0, 2.8, 3, False),
        ]
        vc_map: dict[str, ModelVersion] = {}
        for fam_key, code, display, ver, ctx, file, img, vid, q, s, c, rec in versions_def:
            mv = ModelVersion(
                id=uuid.uuid4(),
                family_id=family_map[fam_key].id,
                code=code,
                display_name=display,
                version_name=ver,
                context_window=ctx,
                supports_files=file,
                supports_images=img,
                supports_video=vid,
                quality_score=q,
                speed_score=s,
                cost_level=c,
                is_recommended=rec,
                input_modalities=["text"] + (["image"] if img else []) + (["video"] if vid else []),
                output_modalities=["text"],
            )
            db.add(mv)
            vc_map[code] = mv
        await db.flush()

        # ── Descriptions (zh-CN) ─────────────────────────────
        descs_def = [
            ("claude-sonnet-4.6", "适合处理长文档、复杂问题和结构化分析任务。",
             ["长文本理解能力强", "结构化输出优秀", "安全对齐好"], ["速度中等", "成本较高"],
             ["长文本理解", "文件分析", "严谨写作"],
             ["总结 PDF", "分析报告", "写长文", "整理资料"]),
            ("gpt-5.6", "综合能力强，适合大多数日常任务和复杂任务。",
             ["通用能力强", "多任务覆盖广", "生态完善"], ["成本较高", "中文不如专用模型"],
             ["通用对话", "写作", "代码", "多任务处理"],
             ["写作", "翻译", "代码解释", "方案生成"]),
            ("deepseek-v4-pro", "适合代码、逻辑推理和中文场景下的复杂任务。",
             ["推理能力强", "代码质量高", "中文优秀"], ["速度中等", "多模态弱"],
             ["推理", "编程", "中文任务", "复杂分析"],
             ["代码生成", "解释报错", "逻辑分析", "中文长文处理"]),
            ("gemini-1.0-ultra", "适合图文理解、多模态输入和综合信息分析。",
             ["多模态理解", "超长上下文", "搜索增强"], ["成本较高", "中文中等"],
             ["多模态理解", "搜索增强", "综合分析"],
             ["图像理解", "多模态分析", "搜索增强", "资料整理"]),
            ("deepseek-v4-flash", "速度快、成本低，适合日常对话和轻量快速任务。",
             ["速度快", "成本低", "轻量好用"], ["能力有限", "不支持文件"],
             ["快速回复", "日常对话", "轻量任务"],
             ["日常问答", "快速翻译", "简短回复"]),
            ("gpt-5.5", "稳定可靠的通用模型，适合写作、翻译和日常对话。",
             ["通用稳定", "写作质量好"], ["不是最新版本"],
             ["通用对话", "写作", "翻译"],
             ["日常写作", "翻译润色", "信息整理"]),
            ("claude-sonnet-4.5", "适合文档处理、内容整理和知识问答。",
             ["文档处理好", "安全可靠"], ["非最新模型"],
             ["文档分析", "内容整理", "问答"],
             ["文档分析", "知识问答", "内容整理"]),
            ("glm-5.2", "擅长中文场景下的对话、知识问答和文档处理。",
             ["中文优秀", "国产可控"], ["英文中等", "生态较新"],
             ["中文对话", "知识问答", "文档处理"],
             ["中文长文", "知识问答", "文档总结"]),
            ("qwen3.7-max", "中文理解能力强，适合长文本处理和综合任务。",
             ["中文理解好", "长文本支持"], ["多模态有限"],
             ["中文理解", "长文本", "综合任务"],
             ["中文写作", "长文处理", "综合问答"]),
            ("kimi-k2.7-code", "专注代码和长文本处理，适合技术场景。",
             ["代码能力强", "超长上下文"], ["通用任务不如旗舰"],
             ["代码编程", "技术问答", "长文本"],
             ["代码编程", "技术文档", "长文分析"]),
        ]
        for code, short, strengths, weaknesses, best_for, example_tasks in descs_def:
            d = ModelDescription(
                id=uuid.uuid4(),
                model_version_id=vc_map[code].id,
                language_code="zh-CN",
                short_description=short,
                strengths=strengths,
                weaknesses=weaknesses,
                best_for=best_for,
                example_tasks=example_tasks,
            )
            db.add(d)
        await db.flush()

        # ── Version ↔ Capabilities ───────────────────────────
        caps_link = {
            "claude-sonnet-4.6": ["long_context", "file_analysis", "writing", "reasoning", "text_chat", "image_understanding"],
            "gpt-5.6": ["text_chat", "writing", "code_gen", "file_analysis", "reasoning", "image_understanding"],
            "deepseek-v4-pro": ["reasoning", "code_gen", "text_chat", "writing", "file_analysis"],
            "gemini-1.0-ultra": ["multimodal", "long_context", "search", "text_chat", "file_analysis", "image_understanding"],
            "deepseek-v4-flash": ["text_chat", "fast_reply", "writing", "code_gen"],
            "gpt-5.5": ["text_chat", "writing", "file_analysis", "image_understanding"],
            "claude-sonnet-4.5": ["text_chat", "file_analysis", "writing", "image_understanding"],
            "glm-5.2": ["text_chat", "writing", "file_analysis", "reasoning", "image_understanding"],
            "qwen3.7-max": ["text_chat", "long_context", "writing", "file_analysis"],
            "kimi-k2.7-code": ["code_gen", "long_context", "text_chat", "reasoning"],
        }
        for code, caps in caps_link.items():
            for cap_code in caps:
                vc = ModelVersionCapability(
                    id=uuid.uuid4(),
                    model_version_id=vc_map[code].id,
                    capability_id=cap_map[cap_code].id,
                    level=4 if cap_code in caps[:2] else 3,
                )
                db.add(vc)
        await db.flush()

        # ── Pricing ──────────────────────────────────────────
        pricing_def = [
            ("claude-sonnet-4.6", "token", 0.0030, 0.0150, 1.5),
            ("gpt-5.6", "token", 0.0050, 0.0150, 1.5),
            ("deepseek-v4-pro", "token", 0.0014, 0.0028, 1.0),
            ("gemini-1.0-ultra", "token", 0.0025, 0.0100, 1.4),
            ("deepseek-v4-flash", "token", 0.0003, 0.0008, 0.3),
            ("gpt-5.5", "token", 0.0030, 0.0150, 1.2),
            ("claude-sonnet-4.5", "token", 0.0030, 0.0150, 1.2),
            ("glm-5.2", "token", 0.0010, 0.0050, 0.8),
            ("qwen3.7-max", "token", 0.0010, 0.0050, 0.8),
            ("kimi-k2.7-code", "token", 0.0010, 0.0050, 0.8),
        ]
        for code, billing, input_price, output_price, quota_rate in pricing_def:
            p = ModelPricing(
                id=uuid.uuid4(),
                model_version_id=vc_map[code].id,
                billing_type=billing,
                input_price_per_1k=input_price,
                output_price_per_1k=output_price,
                quota_cost_rate=quota_rate,
                currency="USD",
            )
            db.add(p)

        await db.commit()
        print(f"✅ Seeded: {len(providers)} providers, {len(families_def)} families, {len(versions_def)} versions")


if __name__ == "__main__":
    asyncio.run(seed())
