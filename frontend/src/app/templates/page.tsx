"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    api
      .listTemplates()
      .then((result) => {
        if (!cancelled) {
          setTemplates(result.templates);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "加载失败");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 space-y-3">
        <Badge>模板中心</Badge>
        <h1 className="text-4xl font-black">办公模板</h1>
        <p className="text-white/70">模板元数据存储在 PostgreSQL，文件通过本地存储或 OSS 托管。</p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>上传模板</CardTitle>
        </CardHeader>
        <CardContent>
          <Input type="file" onChange={() => setError("上传接口已预留，可在下一步对接 /templates/upload")} />
        </CardContent>
      </Card>

      {error && <p className="mb-4 text-sm text-red-300">{error}</p>}

      <div className="grid gap-4">
        {templates.length === 0 ? (
          <Card>
            <CardContent className="p-6 text-white/60">暂无模板，上传后将显示在这里。</CardContent>
          </Card>
        ) : (
          templates.map((item) => (
            <Card key={String(item.id)}>
              <CardHeader>
                <CardTitle>{String(item.name)}</CardTitle>
                <CardDescription>{String(item.size)} bytes</CardDescription>
              </CardHeader>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
