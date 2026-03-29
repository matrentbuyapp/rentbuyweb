"use client";

import Accordion from "@/components/ui/Accordion";
import InputField from "@/components/ui/InputField";
import SelectField from "@/components/ui/SelectField";
import ProGate from "@/components/ui/ProGate";
import ProBadge from "@/components/ui/ProBadge";
import CrashSlider from "./CrashSlider";
import { FormData } from "@/lib/types";

const DELAY_LABELS = ["Buy now", "3 mo", "6 mo", "12 mo", "18 mo", "24 mo"];
const DELAY_VALUES = [0, 3, 6, 12, 18, 24];

interface ZipInfo {
  price: number;
  tax_rate: number | null;
}

interface Props {
  formData: FormData;
  updateField: <K extends keyof FormData>(field: K, value: FormData[K]) => void;
  hasRun: boolean;
  isPro?: boolean;
  zipLookup?: (zip: string) => ZipInfo | null;
  nationalMedian?: number;
  onZipFocus?: () => void;
  lastHousePrice?: number | null;
}

export default function SettingsPanel({ formData, updateField, hasRun, isPro, zipLookup, nationalMedian, onZipFocus, lastHousePrice }: Props) {
  const pro = !!isPro;
  const delayIdx = DELAY_VALUES.indexOf(formData.buy_delay_months);
  const maxStay = formData.years - Math.ceil(formData.buy_delay_months / 12);
  const stayYears = Math.min(formData.stay_years, maxStay);

  const handleStayChange = (v: number) => {
    updateField("stay_years", Math.min(v, maxStay));
  };

  const handleYearsChange = (v: number) => {
    updateField("years", v);
    const newMaxStay = v - Math.ceil(formData.buy_delay_months / 12);
    if (formData.stay_years > newMaxStay) {
      updateField("stay_years", Math.max(1, newMaxStay));
    }
  };

  const handleDelayChange = (v: number) => {
    updateField("buy_delay_months", v);
    const newMaxStay = formData.years - Math.ceil(v / 12);
    if (formData.stay_years > newMaxStay) {
      updateField("stay_years", Math.max(1, newMaxStay));
    }
  };

  const zipInfo = zipLookup?.(formData.zip_code) ?? null;
  const defaultPrice = zipInfo?.price ?? nationalMedian ?? 277000;
  const resolvedPriceLabel = lastHousePrice
    ? `$${lastHousePrice.toLocaleString()} (from last run)`
    : `$${defaultPrice.toLocaleString()} (${zipInfo ? "ZIP median" : "national median"})`;

  const stayLabel = stayYears === formData.years && formData.buy_delay_months === 0
    ? "Own for the full horizon"
    : `Own for ${stayYears} year${stayYears !== 1 ? "s" : ""}, then sell`;

  return (
    <div className="space-y-2">
      {hasRun && (
        <p className="text-xs text-gray-400 px-1 mb-1">
          Change any setting, then hit Re-Calculate to see updated results.
        </p>
      )}

      {/* ===== WHERE & WHAT ===== */}
      <Accordion
        title="Where & What"
        subtitle={`${stayYears}-year ownership${formData.zip_code ? ` · ZIP ${formData.zip_code}` : " · national averages"}`}
        icon={<span>&#x1f3e0;</span>}
        accentColor="bg-emerald-50 text-emerald-600"
      >
        <InputField
          label="ZIP Code"
          value={formData.zip_code}
          onChange={(v) => updateField("zip_code", v)}
          onFocus={onZipFocus}
          placeholder="e.g. 10001"
          hint={zipInfo
            ? `Median home price: $${zipInfo.price.toLocaleString()}${zipInfo.tax_rate != null ? ` · Tax rate: ${(zipInfo.tax_rate * 100).toFixed(2)}%` : ""}`
            : "We'll look up local home prices, taxes, and trends. Leave blank for national averages."}
          compact
        />
        <InputField
          label="Home Price"
          value={formData.house_price}
          onChange={(v) => updateField("house_price", v)}
          prefix="$"
          placeholder={resolvedPriceLabel}
          hint={formData.house_price
            ? "Using your custom price."
            : zipInfo
              ? `Defaults to ZIP median: $${zipInfo.price.toLocaleString()}`
              : `Defaults to national median: $${(nationalMedian ?? 277000).toLocaleString()}`}
        />
        {/* stay_years — free tier */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1.5">
            How long do you plan to own?
          </label>
          <input
            type="range"
            min={1}
            max={Math.max(1, maxStay)}
            step={1}
            value={stayYears}
            onChange={(e) => handleStayChange(Number(e.target.value))}
            className="w-full mt-1"
            style={{ background: "linear-gradient(90deg, #c7d2fe, #e0e7ff)" }}
          />
          <div className="flex justify-between mt-1">
            <span className="text-[10px] text-gray-400">1 yr</span>
            <span className="text-[10px] font-semibold text-indigo-600">{stayYears} year{stayYears !== 1 ? "s" : ""}</span>
            <span className="text-[10px] text-gray-400">{maxStay} yr</span>
          </div>
          <p className="text-[11px] text-gray-400 mt-0.5">{stayLabel}</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <InputField
            label="Down Payment"
            value={formData.down_payment_pct}
            onChange={(v) => updateField("down_payment_pct", Number(v) || 0)}
            suffix="%"
            hint="8% is typical for first-time buyers"
            compact
          />
          {/* buy_delay_months — PRO */}
          <ProGate isPro={pro} label="Delay purchase timing">
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
                onChange={(e) => handleDelayChange(DELAY_VALUES[Number(e.target.value)])}
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
          </ProGate>
        </div>
        {/* PRO: planning horizon */}
        <ProGate isPro={pro} label="Custom planning horizon (2–15 years)">
          <div className="pt-2 border-t border-gray-100">
            <label className="block text-xs font-medium text-gray-500 mb-1.5">
              Planning Horizon
            </label>
            <input
              type="range"
              min={2}
              max={15}
              step={1}
              value={formData.years}
              onChange={(e) => handleYearsChange(Number(e.target.value))}
              className="w-full mt-1"
              style={{ background: "linear-gradient(90deg, #c7d2fe, #e0e7ff)" }}
            />
            <div className="flex justify-between mt-1">
              <span className="text-[10px] text-gray-400">2 yr</span>
              <span className="text-[10px] font-semibold text-indigo-600">{formData.years} years</span>
              <span className="text-[10px] text-gray-400">15 yr</span>
            </div>
            <p className="text-[11px] text-gray-400 mt-0.5">
              Total analysis window. Ownership period ({stayYears} yr) fits within this.
            </p>
          </div>
        </ProGate>
      </Accordion>

      {/* ===== YOUR MORTGAGE ===== */}
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
        {/* PRO: rate forecast overrides */}
        <ProGate isPro={pro} label="Custom rate forecast target and volatility">
          <div className="pt-2 border-t border-gray-100 grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">
                Rate Target
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={formData.mortgage_rate ? "" : ""}
                  placeholder="Auto (20y avg)"
                  className="rounded-xl border border-gray-200 bg-white/80 px-3 py-2.5 text-sm w-28
                    focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100 outline-none transition-all
                    placeholder:text-gray-300 pr-8"
                  onChange={() => {}}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">%</span>
              </div>
              <p className="text-[11px] text-gray-400 mt-1">Where rates will settle long-term</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">
                Rate Volatility
              </label>
              <SelectField
                label=""
                value="1.0"
                onChange={() => {}}
                options={[
                  { value: "0.5", label: "Calm (0.5\u00d7)" },
                  { value: "1.0", label: "Normal (1\u00d7)" },
                  { value: "1.5", label: "Choppy (1.5\u00d7)" },
                  { value: "2.0", label: "Turbulent (2\u00d7)" },
                ]}
                hint="How much rates bounce around the target"
              />
            </div>
          </div>
        </ProGate>
      </Accordion>

      {/* ===== BUYING COSTS ===== */}
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

      {/* ===== INCOME & TAXES ===== */}
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

      {/* ===== MARKET OUTLOOK ===== */}
      <Accordion
        title="Market Outlook"
        subtitle={formData.outlook_preset === "historical" ? "Using historical data" : `Outlook: ${formData.outlook_preset}`}
        icon={<span>&#x1f4c8;</span>}
        accentColor="bg-rose-50 text-rose-600"
      >
        <SelectField
          label="Investment Style"
          value={formData.risk_appetite}
          onChange={(v) => updateField("risk_appetite", v)}
          options={[
            { value: "savings_only", label: "Savings account only \u2014 no market risk" },
            { value: "conservative", label: "Conservative \u2014 lower risk, lower returns" },
            { value: "moderate", label: "Moderate \u2014 typical market returns" },
            { value: "aggressive", label: "Aggressive \u2014 higher risk, higher potential" },
          ]}
          hint={formData.risk_appetite === "savings_only"
            ? "Surplus cash earns 4.5% APY in a savings account. No stock market exposure. Makes buying look relatively better."
            : "Controls stock market exposure for surplus cash. Conservative = 0.5\u00d7, moderate = 1\u00d7, aggressive = 1.5\u00d7 market swings."}
        />
        <CrashSlider
          value={formData.outlook_preset}
          onChange={(v) => updateField("outlook_preset", v)}
        />

        {/* PRO: custom crash overrides */}
        <ProGate isPro={pro} label="Custom crash severity, recovery, and independent stock vs housing shocks">
          <div className="pt-3 border-t border-gray-100 space-y-4">
            <p className="text-[11px] text-gray-500 font-medium">Housing Crash</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] text-gray-500 mb-1">Probability</label>
                <input type="range" min={0} max={100} step={5}
                  value={Math.round((formData.housing_crash_prob ?? 0) * 100)}
                  onChange={(e) => updateField("housing_crash_prob", Number(e.target.value) / 100)}
                  className="w-full" style={{ background: "linear-gradient(90deg, #bbf7d0, #fecaca)" }}
                />
                <span className="text-[10px] text-gray-400">{Math.round((formData.housing_crash_prob ?? 0) * 100)}%</span>
              </div>
              <div>
                <label className="block text-[11px] text-gray-500 mb-1">Drop Severity</label>
                <input type="range" min={0} max={50} step={5}
                  value={Math.round((formData.housing_crash_drop ?? 0) * 100)}
                  onChange={(e) => updateField("housing_crash_drop", Number(e.target.value) / 100)}
                  className="w-full" style={{ background: "linear-gradient(90deg, #bbf7d0, #fecaca)" }}
                />
                <span className="text-[10px] text-gray-400">{Math.round((formData.housing_crash_drop ?? 0) * 100)}% drop</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] text-gray-500 mb-1">Recovery</label>
                <input type="range" min={0} max={100} step={10}
                  value={Math.round((formData.housing_recovery_pct ?? 0.5) * 100)}
                  onChange={(e) => updateField("housing_recovery_pct", Number(e.target.value) / 100)}
                  className="w-full" style={{ background: "linear-gradient(90deg, #fecaca, #bbf7d0)" }}
                />
                <span className="text-[10px] text-gray-400">{Math.round((formData.housing_recovery_pct ?? 0.5) * 100)}% recovers</span>
              </div>
              <div>
                <label className="block text-[11px] text-gray-500 mb-1">Recovery Time</label>
                <input type="range" min={12} max={120} step={12}
                  value={formData.housing_recovery_months ?? 60}
                  onChange={(e) => updateField("housing_recovery_months", Number(e.target.value))}
                  className="w-full" style={{ background: "linear-gradient(90deg, #c7d2fe, #e0e7ff)" }}
                />
                <span className="text-[10px] text-gray-400">{Math.round((formData.housing_recovery_months ?? 60) / 12)} years</span>
              </div>
            </div>

            <p className="text-[11px] text-gray-500 font-medium pt-2">Stock Market Crash</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] text-gray-500 mb-1">Probability</label>
                <input type="range" min={0} max={100} step={5}
                  value={Math.round((formData.stock_crash_prob ?? 0) * 100)}
                  onChange={(e) => updateField("stock_crash_prob", Number(e.target.value) / 100)}
                  className="w-full" style={{ background: "linear-gradient(90deg, #bbf7d0, #fecaca)" }}
                />
                <span className="text-[10px] text-gray-400">{Math.round((formData.stock_crash_prob ?? 0) * 100)}%</span>
              </div>
              <div>
                <label className="block text-[11px] text-gray-500 mb-1">Drop Severity</label>
                <input type="range" min={0} max={60} step={5}
                  value={Math.round((formData.stock_crash_drop ?? 0) * 100)}
                  onChange={(e) => updateField("stock_crash_drop", Number(e.target.value) / 100)}
                  className="w-full" style={{ background: "linear-gradient(90deg, #bbf7d0, #fecaca)" }}
                />
                <span className="text-[10px] text-gray-400">{Math.round((formData.stock_crash_drop ?? 0) * 100)}% drop</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] text-gray-500 mb-1">Recovery</label>
                <input type="range" min={0} max={100} step={10}
                  value={Math.round((formData.stock_recovery_pct ?? 0.7) * 100)}
                  onChange={(e) => updateField("stock_recovery_pct", Number(e.target.value) / 100)}
                  className="w-full" style={{ background: "linear-gradient(90deg, #fecaca, #bbf7d0)" }}
                />
                <span className="text-[10px] text-gray-400">{Math.round((formData.stock_recovery_pct ?? 0.7) * 100)}% recovers</span>
              </div>
              <div>
                <label className="block text-[11px] text-gray-500 mb-1">Recovery Time</label>
                <input type="range" min={6} max={72} step={6}
                  value={formData.stock_recovery_months ?? 36}
                  onChange={(e) => updateField("stock_recovery_months", Number(e.target.value))}
                  className="w-full" style={{ background: "linear-gradient(90deg, #c7d2fe, #e0e7ff)" }}
                />
                <span className="text-[10px] text-gray-400">{Math.round((formData.stock_recovery_months ?? 36) / 12)} years</span>
              </div>
            </div>
          </div>
        </ProGate>
      </Accordion>
    </div>
  );
}
