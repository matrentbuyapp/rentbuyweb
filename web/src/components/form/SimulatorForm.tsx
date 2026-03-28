"use client";

import StepIndicator from "@/components/ui/StepIndicator";
import StepAboutYou from "./StepAboutYou";
import StepBuying from "./StepBuying";
import StepCosts from "./StepCosts";
import StepAdvanced from "./StepAdvanced";
import { FormData } from "@/lib/types";

interface Props {
  formData: FormData;
  updateField: <K extends keyof FormData>(field: K, value: FormData[K]) => void;
  step: number;
  setStep: (s: number) => void;
  loading: boolean;
  onSubmit: () => void;
}

export default function SimulatorForm({
  formData,
  updateField,
  step,
  setStep,
  loading,
  onSubmit,
}: Props) {
  const canSubmit = formData.monthly_rent > 0 && formData.monthly_budget > 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold mb-4">Configure Simulation</h2>
      <StepIndicator current={step} />

      <div className="min-h-[320px]">
        {step === 1 && <StepAboutYou formData={formData} updateField={updateField} />}
        {step === 2 && <StepBuying formData={formData} updateField={updateField} />}
        {step === 3 && <StepCosts formData={formData} updateField={updateField} />}
        {step === 4 && <StepAdvanced formData={formData} updateField={updateField} />}
      </div>

      <div className="flex justify-between mt-6 pt-4 border-t border-gray-100">
        <button
          onClick={() => setStep(step - 1)}
          disabled={step === 1}
          className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg
            hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Back
        </button>
        {step < 4 ? (
          <button
            onClick={() => setStep(step + 1)}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
          >
            Next
          </button>
        ) : (
          <button
            onClick={onSubmit}
            disabled={loading || !canSubmit}
            className="px-6 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg
              hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading && (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {loading ? "Running..." : "Calculate"}
          </button>
        )}
      </div>
    </div>
  );
}
