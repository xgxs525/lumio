"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";

type Message = { role: "user" | "assistant"; content: string };

export default function AiPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "你好，我是序光 AI 办公助手。可以帮你写公式、分析表格、整理办公文档要点。",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    if (!input.trim()) return;
    const nextMessages: Message[] = [...messages, { role: "user", content: input.trim() }];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    try {
      const result = await api.chat(nextMessages);
      setMessages([...nextMessages, { role: "assistant", content: result.data.content }]);
    } catch (err) {
      setMessages([
        ...nextMessages,
        {
          role: "assistant",
          content: err instanceof Error ? err.message : "AI 请求失败",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <div className="mb-8 space-y-3">
        <Badge>AI Gateway</Badge>
        <h1 className="text-4xl font-black">AI 办公助手</h1>
        <p className="text-white/70">统一通过 AI Gateway 调用大模型，支持后续接入多模型路由与审计。</p>
      </div>

      <Card className="min-h-[520px]">
        <CardHeader>
          <CardTitle>对话</CardTitle>
          <CardDescription>配置 AI_GATEWAY_API_KEY 后即可接入真实模型。</CardDescription>
        </CardHeader>
        <CardContent className="flex h-[420px] flex-col gap-4">
          <div className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-white/10 bg-black/20 p-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-7 ${
                  message.role === "user"
                    ? "ml-auto bg-cyan-400/20 text-cyan-50"
                    : "bg-white/10 text-white/85"
                }`}
              >
                {message.content}
              </div>
            ))}
          </div>
          <div className="flex gap-3">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="例如：帮我写一个按部门汇总销售额的 Excel 公式"
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleSend();
              }}
            />
            <Button disabled={loading} onClick={() => void handleSend()}>
              {loading ? "思考中..." : "发送"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
