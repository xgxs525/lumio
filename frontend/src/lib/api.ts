const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.error || `请求失败: ${response.status}`);
  }
  return data as T;
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  uploadFile: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{
      success: boolean;
      filename: string;
      filepath: string;
      storageKey: string;
      size: number;
    }>("/files/upload", { method: "POST", body: form });
  },

  getColumns: (payload: { filepath?: string; storageKey?: string; headerRow?: number }) =>
    request<{ success: boolean; columns: string[]; headerRow: number }>("/files/columns", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  previewSplit: (payload: Record<string, unknown>) =>
    request<Record<string, unknown>>("/tasks/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  createSplitTask: (payload: Record<string, unknown>) =>
    request<{ success: boolean; taskId: string }>("/tasks/split", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  getTask: (taskId: string) =>
    request<{ success: boolean; task: Record<string, unknown> }>(`/tasks/${taskId}`),

  chat: (messages: { role: string; content: string }[]) =>
    request<{ success: boolean; data: { content: string; model: string; mock?: boolean } }>(
      "/ai/chat",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages }),
      },
    ),

  listTemplates: () =>
    request<{ success: boolean; templates: Array<Record<string, unknown>> }>("/templates"),
};
