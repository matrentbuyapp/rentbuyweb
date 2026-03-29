"use client";

const PRESETS = ["optimistic", "historical", "cautious", "pessimistic", "crisis"];
const LABELS = ["Optimistic", "Historical", "Cautious", "Pessimistic", "Crisis"];
const DESCRIPTIONS: Record<string, string> = {
  optimistic: "Lower-than-normal market volatility. No downturn scenarios added. Good times ahead.",
  historical: "Normal market behavior based on real historical data. No extra downturn scenarios added.",
  cautious: "Slightly elevated volatility. In 10% of simulations, homes dip ~10% and stocks dip ~15%.",
  pessimistic: "Elevated volatility. In 25% of simulations, homes drop ~20% and stocks drop ~25%.",
  crisis: "High volatility. In half of simulations, homes drop ~30% and stocks drop ~35%.",
};

interface Props {
  value: string;
  onChange: (value: string) => void;
}

export default function CrashSlider({ value, onChange }: Props) {
  const idx = PRESETS.indexOf(value);

  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1.5">
        Market outlook
      </label>
      <p className="text-[11px] text-gray-400 mb-3 leading-snug">
        Our simulations use real historical market data. This slider adjusts
        how much extra caution you want to build in — move it right if you
        think conditions ahead are worse than usual.
      </p>
      <input
        type="range"
        min={0}
        max={4}
        step={1}
        value={idx >= 0 ? idx : 1}
        onChange={(e) => onChange(PRESETS[Number(e.target.value)])}
        className="w-full"
        style={{
          background: `linear-gradient(90deg, #bbf7d0 0%, #fef08a 50%, #fecaca 100%)`,
        }}
      />
      <div className="flex justify-between mt-2 px-0.5">
        {LABELS.map((label, i) => (
          <span
            key={i}
            className={`text-[10px] text-center leading-tight transition-all ${
              i === idx
                ? "font-semibold text-gray-700"
                : "text-gray-400"
            }`}
          >
            {label}
          </span>
        ))}
      </div>
      <p className="text-[11px] text-gray-400 mt-2.5 leading-snug italic">
        {DESCRIPTIONS[value] || DESCRIPTIONS.historical}
      </p>
    </div>
  );
}
