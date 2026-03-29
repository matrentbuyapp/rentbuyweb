"use client";

interface InputFieldProps {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  onFocus?: () => void;
  prefix?: string;
  suffix?: string;
  placeholder?: string;
  type?: string;
  required?: boolean;
  hint?: string;
  compact?: boolean;
}

export default function InputField({
  label,
  value,
  onChange,
  onFocus,
  prefix,
  suffix,
  placeholder,
  type = "text",
  required,
  hint,
  compact,
}: InputFieldProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1.5">
        {label}
        {required && <span className="text-rose-400 ml-0.5">*</span>}
      </label>
      <div className="relative">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm pointer-events-none">
            {prefix}
          </span>
        )}
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={onFocus}
          placeholder={placeholder}
          className={`rounded-xl border border-gray-200 bg-white/80 backdrop-blur-sm px-3 py-2.5 text-sm
            focus:border-indigo-300 focus:ring-2 focus:ring-indigo-100 outline-none transition-all
            placeholder:text-gray-300
            ${compact ? "w-28" : "w-full"}
            ${prefix ? "pl-7" : ""} ${suffix ? "pr-8" : ""}`}
        />
        {suffix && (
          <span className={`absolute top-1/2 -translate-y-1/2 text-gray-400 text-sm pointer-events-none
            ${compact ? "left-[7.5rem] ml-2" : "right-3"}`}>
            {suffix}
          </span>
        )}
      </div>
      {hint && <p className="text-[11px] text-gray-400 mt-1 leading-snug">{hint}</p>}
    </div>
  );
}
