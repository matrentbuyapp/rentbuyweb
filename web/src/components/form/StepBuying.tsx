"use client";

import InputField from "@/components/ui/InputField";
import SelectField from "@/components/ui/SelectField";
import { FormData } from "@/lib/types";

interface Props {
  formData: FormData;
  updateField: <K extends keyof FormData>(field: K, value: FormData[K]) => void;
}

export default function StepBuying({ formData, updateField }: Props) {
  return (
    <div className="space-y-4">
      <InputField
        label="ZIP Code"
        value={formData.zip_code}
        onChange={(v) => updateField("zip_code", v)}
        placeholder="e.g. 10001 (optional)"
      />
      <InputField
        label="Home Price"
        value={formData.house_price}
        onChange={(v) => updateField("house_price", v)}
        prefix="$"
        placeholder="Leave blank to auto-estimate"
      />
      <InputField
        label="Down Payment"
        value={formData.down_payment_pct}
        onChange={(v) => updateField("down_payment_pct", Number(v) || 0)}
        suffix="%"
      />
      <SelectField
        label="Credit Quality"
        value={formData.credit_quality}
        onChange={(v) => updateField("credit_quality", v)}
        options={[
          { value: "excellent", label: "Excellent (760+)" },
          { value: "great", label: "Great (720-759)" },
          { value: "good", label: "Good (680-719)" },
          { value: "average", label: "Average (640-679)" },
          { value: "mediocre", label: "Mediocre (600-639)" },
          { value: "poor", label: "Poor (<600)" },
        ]}
      />
      <div className="grid grid-cols-2 gap-3">
        <SelectField
          label="Loan Term"
          value={String(formData.term_years)}
          onChange={(v) => updateField("term_years", Number(v))}
          options={[
            { value: "30", label: "30 years" },
            { value: "15", label: "15 years" },
          ]}
        />
        <InputField
          label="Buy Delay"
          value={formData.buy_delay_months}
          onChange={(v) => updateField("buy_delay_months", Number(v) || 0)}
          suffix="mo"
        />
      </div>
    </div>
  );
}
