import Link from "next/link";
import { ArrowRight, Bot, FileSpreadsheet, Layers, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const features = [
  {
    icon: FileSpreadsheet,
    title: "智能表格处理",
    description: "拆分、合并、去重、清洗、转换与批量处理，覆盖常见办公表格场景。",
  },
  {
    icon: Bot,
    title: "AI 办公助手",
    description: "通过 AI Gateway 统一接入大模型，辅助写公式、分析数据、生成报表说明。",
  },
  {
    icon: Layers,
    title: "模板与协作",
    description: "模板中心、云盘、知识库与工作台，为团队办公协作提供统一入口。",
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-16">
      <section className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-6">
          <Badge className="gap-2">
            <Sparkles className="h-3.5 w-3.5" />
            新一代 AI 智能办公平台
          </Badge>
          <h1 className="max-w-3xl text-5xl font-black leading-tight tracking-tight md:text-6xl">
            让表格处理、AI 协作与团队办公，在一个平台里完成
          </h1>
          <p className="max-w-2xl text-lg leading-8 text-white/75">
            序光基于 FastAPI + PostgreSQL + Redis + Celery + OSS 构建后端能力，
            前端采用 Next.js + React + TypeScript + Tailwind + shadcn/ui，面向真实业务持续演进。
          </p>
          <div className="flex flex-wrap gap-3">
            <Button size="lg" asChild>
              <Link href="/split">
                立即拆分表格
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="secondary" asChild>
              <Link href="/ai">体验 AI 助手</Link>
            </Button>
          </div>
        </div>

        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle>平台能力矩阵</CardTitle>
            <CardDescription>从原型页面升级为可扩展的生产级架构。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="rounded-xl border border-white/10 bg-white/5 p-4"
              >
                <div className="mb-2 flex items-center gap-2 font-semibold">
                  <feature.icon className="h-4 w-4 text-cyan-300" />
                  {feature.title}
                </div>
                <p className="text-sm text-white/70">{feature.description}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
