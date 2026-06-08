import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const plans = [
  { name: "免费版", price: "¥0", desc: "基础表格工具与有限 AI 次数。" },
  { name: "专业版", price: "¥49/月", desc: "更高文件上限、批量处理与模板管理。" },
  { name: "团队版", price: "¥199/月", desc: "多人协作、云盘、知识库与权限管理。" },
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <div className="mb-10 text-center">
        <Badge>价格方案</Badge>
        <h1 className="mt-4 text-4xl font-black">选择适合你的办公方案</h1>
      </div>
      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan) => (
          <Card key={plan.name}>
            <CardHeader>
              <CardTitle>{plan.name}</CardTitle>
              <CardDescription>{plan.desc}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-6 text-3xl font-black text-cyan-200">{plan.price}</p>
              <Button className="w-full" variant={plan.name === "专业版" ? "default" : "secondary"}>
                选择方案
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
