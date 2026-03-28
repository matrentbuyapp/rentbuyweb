"use client";

import InputField from "@/components/ui/InputField";
import { FormData } from "@/lib/types";

interface Props {
  formData: FormData;
  updateField: <K extends keyof FormData>(field: K, value: FormData[K]) => void;
}

export default function StepAboutYou({ formData, updateField }: Props) {
  return (
    <div className="space-y-4">
      <InputField
        label="Current Monthly Rent"
        value={formData.monthly_rent}
        onChange={(v) => updateField("monthly_rent", Number(v) || 0)}
        prefix="$"
        required
      />
      <InputField
        label="Total Monthly Housing Budget"
        value={formData.monthly_budget}
        onChange={(v) => updateField("monthly_budget", Number(v) || 0)}
        prefix="$"
        required
      />
      <InputField
        label="Savings Available"
        value={formData.initial_cash}
        onChange={(v) => updateField("initial_cash", Number(v) || 0)}
        prefix="$"
      />
      <InputField
        label="Annual Income"
        value={formData.yearly_income}
        onChange={(v) => updateField("yearly_income", Number(v) || 0)}
        prefix="$"
      />
    </div>
  );
}
