import Link from "next/link";
import { FileSpreadsheet, Sparkles, Wand2 } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const tools = [
  { href: "/split", title: "表格拆分", description: "按列值、行数、工作表拆分 Excel。", icon: FileSpreadsheet },
  { href: "/ai", title: "AI 助手", description: "公式、分析、文档整理与办公问答。", icon: Sparkles },
  { href: "/templates", title: "模板中心", description: "浏览与上传自定义办公模板。", icon: Wand2 },
];

export default function ToolsPage() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <h1 className="mb-8 text-4xl font-black">工具中心</h1>
      <div className="grid gap-6 md:grid-cols-3">
        {tools.map((tool) => (
          <Link key={tool.href} href={tool.href}>
            <Card className="h-full transition hover:border-cyan-300/30 hover:bg-white/10">
              <CardHeader>
                <tool.icon className="mb-2 h-6 w-6 text-cyan-300" />
                <CardTitle>{tool.title}</CardTitle>
                <CardDescription>{tool.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <span className="text-sm font-semibold text-cyan-200">进入工具 →</span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
