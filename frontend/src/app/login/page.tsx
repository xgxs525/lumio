import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md items-center px-6 py-12">
      <Card className="w-full">
        <CardHeader>
          <CardTitle>登录序光</CardTitle>
          <CardDescription>账号体系将接入 PostgreSQL 用户表与 JWT 鉴权。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input placeholder="邮箱" type="email" />
          <Input placeholder="密码" type="password" />
          <Button className="w-full">登录</Button>
          <p className="text-center text-sm text-white/60">
            还没有账号？{" "}
            <Link href="/register" className="text-cyan-300 hover:underline">
              立即注册
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
