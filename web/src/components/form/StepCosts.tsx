"use client";

import InputField from "@/components/ui/InputField";
import { FormData } from "@/lib/types";

interface Props {
  formData: FormData;
  updateField: <K extends keyof FormData>(field: K, value: FormData[K]) => void;
}

export default function StepCosts({ formData, updateField }: Props) {
  return (
    <div className="space-y-4">
      <InputField
        label="Closing Costs"
        value={formData.closing_cost_pct}
        onChange={(v) => updateField("closing_cost_pct", Number(v) || 0)}
        suffix="%"
      />
      <InputField
        label="Move-in Cost"
        value={formData.move_in_cost}
        onChange={(v) => updateField("move_in_cost", Number(v) || 0)}
        prefix="$"
      />
      <InputField
        label="Annual Home Insurance"
        value={formData.insurance_annual}
        onChange={(v) => updateField("insurance_annual", Number(v) || 0)}
        prefix="$"
      />
      <InputField
        label="Annual Maintenance Rate"
        value={formData.maintenance_rate}
        onChange={(v) => updateField("maintenance_rate", Number(v) || 0)}
        suffix="%"
      />
      <InputField
        label="Selling Costs"
        value={formData.sell_cost_pct}
        onChange={(v) => updateField("sell_cost_pct", Number(v) || 0)}
        suffix="%"
      />
    </div>
  );
}
