import { apiFetch } from "@/lib/api";
import { SkuHeader } from "@/components/sku-header";
import { SkuDemandSection } from "@/components/sku-demand-section";
import { SkuStockSection } from "@/components/sku-stock-section";
import { SkuSupplierSection } from "@/components/sku-supplier-section";
import { SkuScenarioSection } from "@/components/sku-scenario-section";
import type { SkuProfile } from "@/lib/api";

interface Props {
  params: Promise<{ sku_id: string }>;
}

export default async function SkuDeepDivePage({ params }: Props) {
  const { sku_id } = await params;
  const sku = await apiFetch<SkuProfile>(`/api/sku/${sku_id}`);

  if (!sku) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-2 text-gray-400">
        <p className="text-lg font-medium">SKU not found</p>
        <p className="text-sm">{sku_id} — check the ID or make sure the backend is running.</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <SkuHeader sku={sku} />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <SkuStockSection sku={sku} />
        <SkuSupplierSection sku={sku} />
      </div>

      <SkuDemandSection sku={sku} />
      <SkuScenarioSection skuId={sku_id} />
    </div>
  );
}
