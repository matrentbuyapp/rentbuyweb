"use client";

import InputField from "@/components/ui/InputField";
import SelectField from "@/components/ui/SelectField";
import CrashSlider from "./CrashSlider";
import { FormData } from "@/lib/types";

interface Props {
  formData: FormData;
  updateField: <K extends keyof FormData>(field: K, value: FormData[K]) => void;
}

export default function StepAdvanced({ formData, updateField }: Props) {
  return (
    <div className="space-y-4">
      <SelectField
        label="Risk Appetite"
        value={formData.risk_appetite}
        onChange={(v) => updateField("risk_appetite", v)}
        options={[
          { value: "conservative", label: "Conservative (0.5x stock allocation)" },
          { value: "moderate", label: "Moderate (1x)" },
          { value: "aggressive", label: "Aggressive (1.5x)" },
        ]}
      />
      <SelectField
        label="Filing Status"
        value={formData.filing_status}
        onChange={(v) => updateField("filing_status", v)}
        options={[
          { value: "single", label: "Single" },
          { value: "married_joint", label: "Married Filing Jointly" },
          { value: "head_of_household", label: "Head of Household" },
        ]}
      />
      <InputField
        label="Other Itemized Deductions"
        value={formData.other_deductions}
        onChange={(v) => updateField("other_deductions", Number(v) || 0)}
        prefix="$"
        placeholder="0"
      />
      <InputField
        label="Mortgage Rate Override"
        value={formData.mortgage_rate}
        onChange={(v) => updateField("mortgage_rate", v)}
        suffix="%"
        placeholder="Leave blank for current rate"
      />
      <div className="grid grid-cols-2 gap-3">
        <InputField
          label="Simulation Years"
          value={formData.years}
          onChange={(v) => updateField("years", Number(v) || 10)}
        />
        <InputField
          label="Simulations"
          value={formData.num_simulations}
          onChange={(v) => updateField("num_simulations", Number(v) || 500)}
        />
      </div>
      <CrashSlider
        value={formData.outlook_preset}
        onChange={(v) => updateField("outlook_preset", v)}
      />
    </div>
  );
}
