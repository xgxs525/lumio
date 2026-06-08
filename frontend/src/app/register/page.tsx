import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function RegisterPage() {
  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md items-center px-6 py-12">
      <Card className="w-full">
        <CardHeader>
          <CardTitle>注册账号</CardTitle>
          <CardDescription>注册信息将写入 PostgreSQL，并支持后续会员体系扩展。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input placeholder="昵称" />
          <Input placeholder="邮箱" type="email" />
          <Input placeholder="密码" type="password" />
          <Button className="w-full">创建账号</Button>
          <p className="text-center text-sm text-white/60">
            已有账号？{" "}
            <Link href="/login" className="text-cyan-300 hover:underline">
              去登录
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
