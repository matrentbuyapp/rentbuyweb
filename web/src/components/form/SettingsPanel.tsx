"use client";

import Accordion from "@/components/ui/Accordion";
import InputField from "@/components/ui/InputField";
import SelectField from "@/components/ui/SelectField";
import CrashSlider from "./CrashSlider";
import { FormData } from "@/lib/types";

const DELAY_LABELS = ["Buy now", "3 mo", "6 mo", "12 mo", "18 mo", "24 mo"];
const DELAY_VALUES = [0, 3, 6, 12, 18, 24];

interface Props {
  formData: FormData;
  updateField: <K extends keyof FormData>(field: K, value: FormData[K]) => void;
  hasRun: boolean;
}

export default function SettingsPanel({ formData, updateField, hasRun }: Props) {
  const delayIdx = DELAY_VALUES.indexOf(formData.buy_delay_months);

  return (
    <div className="space-y-2">
      {hasRun && (
        <p className="text-xs text-gray-400 px-1 mb-1">
          Change any setting, then hit Re-Calculate to see updated results.
        </p>
      )}

      <Accordion
        title="Where & What"
        subtitle={formData.zip_code ? `ZIP ${formData.zip_code}` : "Using national averages"}
        icon={<span>&#x1f3e0;</span>}
        accentColor="bg-emerald-50 text-emerald-600"
      >
        <InputField
          label="ZIP Code"
          value={formData.zip_code}
          onChange={(v) => updateField("zip_code", v)}
          placeholder="e.g. 10001"
          hint="We'll look up local home prices, taxes, and trends. Leave blank for national averages."
          compact
        />
        <InputField
          label="Home Price"
          value={formData.house_price}
          onChange={(v) => updateField("house_price", v)}
          prefix="$"
          placeholder="We'll estimate for you"
          hint="If you have a specific home in mind, enter its price. Otherwise we'll estimate based on your rent and location."
        />
        <div className="grid grid-cols-2 gap-3">
          <InputField
            label="Down Payment"
            value={formData.down_payment_pct}
            onChange={(v) => updateField("down_payment_pct", Number(v) || 0)}
            suffix="%"
            hint="8% is typical for first-time buyers"
            compact
          />
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">
              When to Buy
            </label>
            <input
              type="range"
              min={0}
              max={5}
              step={1}
              value={delayIdx >= 0 ? delayIdx : 0}
              onChange={(e) => updateField("buy_delay_months", DELAY_VALUES[Number(e.target.value)])}
              className="w-full mt-1"
              style={{ background: "linear-gradient(90deg, #c7d2fe, #e0e7ff)" }}
            />
            <div className="flex justify-between mt-1">
              <span className={`text-[10px] ${delayIdx === 0 ? "font-semibold text-indigo-600" : "text-gray-400"}`}>Now</span>
              <span className={`text-[10px] ${delayIdx === 5 ? "font-semibold text-indigo-600" : "text-gray-400"}`}>2 yr</span>
            </div>
            <p className="text-[11px] text-gray-400 mt-0.5">
              {formData.buy_delay_months === 0
                ? "Buy right away"
                : `Rent for ${formData.buy_delay_months} months first, then buy`}
            </p>
          </div>
        </div>
      </Accordion>

      <Accordion
        title="Your Mortgage"
        subtitle={`${formData.term_years}-year loan, ${formData.credit_quality} credit`}
        icon={<span>&#x1f3e6;</span>}
        accentColor="bg-blue-50 text-blue-600"
      >
        <SelectField
          label="Credit Score Range"
          value={formData.credit_quality}
          onChange={(v) => updateField("credit_quality", v)}
          options={[
            { value: "excellent", label: "Excellent (760+)" },
            { value: "great", label: "Great (720\u2013759)" },
            { value: "good", label: "Good (680\u2013719)" },
            { value: "average", label: "Average (640\u2013679)" },
            { value: "mediocre", label: "Fair (600\u2013639)" },
            { value: "poor", label: "Below 600" },
          ]}
          hint="Your credit score affects the interest rate you'll get. 'Good' is the most common range."
        />
        <div className="grid grid-cols-2 gap-3">
          <SelectField
            label="Loan Length"
            value={String(formData.term_years)}
            onChange={(v) => updateField("term_years", Number(v))}
            options={[
              { value: "30", label: "30 years" },
              { value: "15", label: "15 years" },
            ]}
            hint="30 years = lower payments. 15 years = less interest overall."
          />
          <InputField
            label="Interest Rate"
            value={formData.mortgage_rate}
            onChange={(v) => updateField("mortgage_rate", v)}
            suffix="%"
            placeholder="Auto"
            hint="Leave blank to use today's rate"
            compact
          />
        </div>
      </Accordion>

      <Accordion
        title="Buying Costs"
        subtitle={`${formData.closing_cost_pct}% closing \u00b7 $${formData.insurance_annual.toLocaleString()}/yr insurance`}
        icon={<span>&#x1f4b0;</span>}
        accentColor="bg-amber-50 text-amber-600"
      >
        <div className="grid grid-cols-2 gap-3">
          <InputField
            label="Closing Costs"
            value={formData.closing_cost_pct}
            onChange={(v) => updateField("closing_cost_pct", Number(v) || 0)}
            suffix="%"
            hint="Fees paid when you buy (title, appraisal, etc.)"
            compact
          />
          <InputField
            label="Selling Costs"
            value={formData.sell_cost_pct}
            onChange={(v) => updateField("sell_cost_pct", Number(v) || 0)}
            suffix="%"
            hint="Agent fees when you eventually sell"
            compact
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <InputField
            label="Home Insurance"
            value={formData.insurance_annual}
            onChange={(v) => updateField("insurance_annual", Number(v) || 0)}
            prefix="$"
            hint="Per year. $2,000 is a typical US average."
            compact
          />
          <InputField
            label="Upkeep"
            value={formData.maintenance_rate}
            onChange={(v) => updateField("maintenance_rate", Number(v) || 0)}
            suffix="%"
            hint="Yearly repairs as % of home value. 1% is the rule of thumb."
            compact
          />
        </div>
        <InputField
          label="Move-in Cost"
          value={formData.move_in_cost}
          onChange={(v) => updateField("move_in_cost", Number(v) || 0)}
          prefix="$"
          placeholder="0"
          hint="One-time costs like movers, new furniture, etc."
          compact
        />
      </Accordion>

      <Accordion
        title="Income & Taxes"
        subtitle={formData.yearly_income ? `$${formData.yearly_income.toLocaleString()}/yr income` : "Not set"}
        icon={<span>&#x1f4cb;</span>}
        accentColor="bg-violet-50 text-violet-600"
      >
        <InputField
          label="Yearly Income (before taxes)"
          value={formData.yearly_income}
          onChange={(v) => updateField("yearly_income", Number(v) || 0)}
          prefix="$"
          hint="Used to calculate how much you save on taxes by owning. Mortgage interest is tax-deductible."
        />
        <SelectField
          label="Tax Filing Status"
          value={formData.filing_status}
          onChange={(v) => updateField("filing_status", v)}
          options={[
            { value: "single", label: "Single" },
            { value: "married_joint", label: "Married Filing Jointly" },
            { value: "head_of_household", label: "Head of Household" },
          ]}
          hint="This determines your standard deduction and tax bracket."
        />
        <InputField
          label="Other Deductions"
          value={formData.other_deductions}
          onChange={(v) => updateField("other_deductions", Number(v) || 0)}
          prefix="$"
          placeholder="0"
          hint="Charitable donations, medical expenses, etc. Most people can leave this at $0."
        />
      </Accordion>

      <Accordion
        title="Market Outlook"
        subtitle={formData.crash_outlook === "none" ? "Trusting history" : `Extra caution: ${formData.crash_outlook.replace("_", " ")}`}
        icon={<span>&#x1f4c8;</span>}
        accentColor="bg-rose-50 text-rose-600"
      >
        <SelectField
          label="Investment Style"
          value={formData.risk_appetite}
          onChange={(v) => updateField("risk_appetite", v)}
          options={[
            { value: "conservative", label: "Conservative \u2014 lower risk, lower returns" },
            { value: "moderate", label: "Moderate \u2014 typical market returns" },
            { value: "aggressive", label: "Aggressive \u2014 higher risk, higher potential" },
          ]}
          hint="This controls how much of the stock market's ups and downs affect your investment returns. Conservative = half the market swings, aggressive = 1.5x. Applies to both buyer and renter portfolios."
        />
        <CrashSlider
          value={formData.crash_outlook}
          onChange={(v) => updateField("crash_outlook", v)}
        />
      </Accordion>
    </div>
  );
}
