"use client";

const OUTLOOKS = ["none", "unlikely", "possible", "likely", "very_likely"];
const LABELS = ["Trust\nhistory", "A little\nworried", "Somewhat\nworried", "Pretty\nworried", "Very\nworried"];
const DESCRIPTIONS: Record<string, string> = {
  none: "No extra downturn added. The simulation still reflects normal market ups and downs from real historical data.",
  unlikely: "In 5% of simulations, an extra dip is added: homes drop ~15% over a year then recover over 4 years. Stocks drop ~20% then recover over 2 years.",
  possible: "In 15% of simulations, an extra dip is added: homes drop ~20% over a year then recover over 4 years. Stocks drop ~25% then recover over 2 years.",
  likely: "In 30% of simulations, an extra dip is added: homes drop ~25% over a year then recover over 4 years. Stocks drop ~30% then recover over 2 years.",
  very_likely: "In half of all simulations, an extra dip is added: homes drop ~30% over a year then recover over 4 years. Stocks drop ~35% then recover over 2 years.",
};

interface Props {
  value: string;
  onChange: (value: string) => void;
}

export default function CrashSlider({ value, onChange }: Props) {
  const idx = OUTLOOKS.indexOf(value);

  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1.5">
        Are you worried about a downturn?
      </label>
      <p className="text-[11px] text-gray-400 mb-3 leading-snug">
        Our simulations already include normal market swings based on real
        historical data. This slider adds extra concern on top of that \u2014
        move it right if you think conditions ahead are worse than usual.
      </p>
      <input
        type="range"
        min={0}
        max={4}
        step={1}
        value={idx >= 0 ? idx : 2}
        onChange={(e) => onChange(OUTLOOKS[Number(e.target.value)])}
        className="w-full"
        style={{
          background: `linear-gradient(90deg, #bbf7d0 0%, #fef08a 50%, #fecaca 100%)`,
        }}
      />
      <div className="flex justify-between mt-2 px-0.5">
        {LABELS.map((label, i) => (
          <span
            key={i}
            className={`text-[10px] text-center whitespace-pre-line leading-tight transition-all ${
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
        {DESCRIPTIONS[value] || DESCRIPTIONS.possible}
      </p>
    </div>
  );
}
