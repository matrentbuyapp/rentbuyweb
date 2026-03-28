"use client";

const STEPS = ["About You", "Buying", "Costs", "Advanced"];

interface StepIndicatorProps {
  current: number;
}

export default function StepIndicator({ current }: StepIndicatorProps) {
  return (
    <div className="flex items-center gap-1 mb-6">
      {STEPS.map((label, i) => {
        const stepNum = i + 1;
        const active = stepNum === current;
        const done = stepNum < current;
        return (
          <div key={label} className="flex items-center gap-1 flex-1">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold shrink-0
                ${active ? "bg-blue-600 text-white" : done ? "bg-blue-100 text-blue-700" : "bg-gray-200 text-gray-500"}`}
            >
              {done ? "\u2713" : stepNum}
            </div>
            <span className={`text-xs truncate ${active ? "text-blue-700 font-medium" : "text-gray-500"}`}>
              {label}
            </span>
            {i < STEPS.length - 1 && (
              <div className={`h-px flex-1 ${done ? "bg-blue-300" : "bg-gray-200"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
