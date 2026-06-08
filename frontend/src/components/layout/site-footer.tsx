import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-white/10 bg-[#040a1a]/70">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-10 text-sm text-white/60 md:flex-row md:items-center md:justify-between">
        <p>© {new Date().getFullYear()} 序光 · AI 智能办公平台</p>
        <div className="flex gap-4">
          <Link href="/pricing" className="hover:text-white">
            价格方案
          </Link>
          <Link href="/templates" className="hover:text-white">
            模板中心
          </Link>
          <Link href="/ai" className="hover:text-white">
            AI 助手
          </Link>
        </div>
      </div>
    </footer>
  );
}
