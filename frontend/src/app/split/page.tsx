"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

type UploadInfo = {
  filename: string;
  filepath: string;
  storageKey: string;
};

export default function SplitPage() {
  const [upload, setUpload] = useState<UploadInfo | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [column, setColumn] = useState("");
  const [rowsPerFile, setRowsPerFile] = useState("500");
  const [splitType, setSplitType] = useState<"column" | "row_count" | "sheet">("column");
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [task, setTask] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const payload = useMemo(
    () => ({
      filepath: upload?.filepath,
      storageKey: upload?.storageKey,
      splitType,
      column: splitType === "column" ? column : undefined,
      rowsPerFile: splitType === "row_count" ? Number(rowsPerFile) : undefined,
      headerRow: 1,
    }),
    [upload, splitType, column, rowsPerFile],
  );

  async function handleUpload(file: File) {
    setError(null);
    setLoading(true);
    try {
      const result = await api.uploadFile(file);
      const info = {
        filename: result.filename,
        filepath: result.filepath,
        storageKey: result.storageKey,
      };
      setUpload(info);
      const cols = await api.getColumns({ storageKey: result.storageKey, headerRow: 1 });
      setColumns(cols.columns);
      if (cols.columns[0]) setColumn(cols.columns[0]);
      setPreview(null);
      setTask(null);
      setTaskId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传失败");
    } finally {
      setLoading(false);
    }
  }

  async function handlePreview() {
    if (!upload) return;
    setError(null);
    setLoading(true);
    try {
      const result = await api.previewSplit(payload);
      setPreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "预览失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleSplit() {
    if (!upload) return;
    setError(null);
    setLoading(true);
    try {
      const result = await api.createSplitTask(payload);
      setTaskId(result.taskId);
      pollTask(result.taskId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "提交任务失败");
      setLoading(false);
    }
  }

  async function pollTask(id: string) {
    const timer = setInterval(async () => {
      try {
        const result = await api.getTask(id);
        setTask(result.task);
        if (result.task.status === "completed" || result.task.status === "failed") {
          clearInterval(timer);
          setLoading(false);
        }
      } catch (err) {
        clearInterval(timer);
        setLoading(false);
        setError(err instanceof Error ? err.message : "查询任务失败");
      }
    }, 1500);
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 space-y-3">
        <Badge>工具中心 / 表格拆分</Badge>
        <h1 className="text-4xl font-black">表格拆分</h1>
        <p className="text-white/70">
          上传 Excel 文件，按列值、行数或工作表拆分。任务通过 Celery 异步执行，状态写入 PostgreSQL。
        </p>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>1. 上传文件</CardTitle>
            <CardDescription>支持 xlsx / xls / csv 等常见办公格式。</CardDescription>
          </CardHeader>
          <CardContent>
            <Input
              type="file"
              accept=".xlsx,.xls,.xlsm,.csv"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleUpload(file);
              }}
            />
            {upload && (
              <p className="mt-3 text-sm text-cyan-200">已上传：{upload.filename}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>2. 拆分规则</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              {(["column", "row_count", "sheet"] as const).map((type) => (
                <Button
                  key={type}
                  variant={splitType === type ? "default" : "secondary"}
                  onClick={() => setSplitType(type)}
                >
                  {type === "column" ? "按列值" : type === "row_count" ? "按行数" : "按工作表"}
                </Button>
              ))}
            </div>

            {splitType === "column" && (
              <select
                className="h-11 w-full rounded-lg border border-white/15 bg-white/5 px-4 text-sm text-white"
                value={column}
                onChange={(e) => setColumn(e.target.value)}
              >
                {columns.map((col) => (
                  <option key={col} value={col} className="bg-slate-900">
                    {col}
                  </option>
                ))}
              </select>
            )}

            {splitType === "row_count" && (
              <Input
                value={rowsPerFile}
                onChange={(e) => setRowsPerFile(e.target.value)}
                placeholder="每个文件行数"
              />
            )}

            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" disabled={!upload || loading} onClick={() => void handlePreview()}>
                预览结果
              </Button>
              <Button disabled={!upload || loading} onClick={() => void handleSplit()}>
                {loading ? "处理中..." : "开始拆分"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {error && (
          <Card className="border-red-400/30 bg-red-500/10">
            <CardContent className="p-4 text-sm text-red-200">{error}</CardContent>
          </Card>
        )}

        {preview && (
          <Card>
            <CardHeader>
              <CardTitle>预览</CardTitle>
              <CardDescription>预计生成 {String(preview.fileCount ?? 0)} 个文件</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="overflow-auto rounded-xl bg-black/30 p-4 text-xs text-white/80">
                {JSON.stringify(preview, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}

        {taskId && task && (
          <Card>
            <CardHeader>
              <CardTitle>任务状态</CardTitle>
              <CardDescription>任务 ID：{taskId}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-3 text-sm">
                状态：<span className="font-semibold text-cyan-200">{String(task.status)}</span>
              </p>
              <pre className="overflow-auto rounded-xl bg-black/30 p-4 text-xs text-white/80">
                {JSON.stringify(task, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
