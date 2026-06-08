import Link from "next/link";

import { Button } from "@/components/ui/button";

const navItems = [
  { href: "/tools", label: "工具中心" },
  { href: "/split", label: "表格拆分" },
  { href: "/ai", label: "AI 助手" },
  { href: "/templates", label: "模板中心" },
  { href: "/pricing", label: "价格方案" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-[#040a1a]/85 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-4">
        <Link href="/" className="flex items-center gap-3 font-black text-white">
          <span className="grid h-9 w-9 grid-cols-3 gap-1 rounded-lg bg-gradient-to-br from-emerald-300 to-blue-500 p-1.5 shadow-[0_0_24px_rgba(34,244,220,0.35)]">
            {Array.from({ length: 9 }).map((_, i) => (
              <span key={i} className="rounded-sm bg-white/80" />
            ))}
          </span>
          <span className="text-lg">序光</span>
        </Link>

        <nav className="hidden items-center gap-2 md:flex">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-white/75 transition hover:bg-white/10 hover:text-white"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Button variant="ghost" asChild>
            <Link href="/login">登录</Link>
          </Button>
          <Button asChild>
            <Link href="/split">开始使用</Link>
          </Button>
        </div>
      </div>
    </header>
  );
}
