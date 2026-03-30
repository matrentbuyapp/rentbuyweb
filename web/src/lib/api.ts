import { FormData, SummaryRequest, SummaryResponse, Scenario, ScenarioList, Alert, AlertList, WhatIfResponse, SensitivityResponse, TrendResponse, LlmSummaryResponse } from "./types";
import { getDeviceId } from "./device";

export function getApiUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
    return `http://${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

const API_URL = getApiUrl();

function proHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    "X-Device-Id": getDeviceId(),
  };
}

export function formToRequest(form: FormData): SummaryRequest {
  return {
    monthly_rent: form.monthly_rent,
    monthly_budget: form.monthly_budget,
    initial_cash: form.initial_cash,
    yearly_income: form.yearly_income ? Number(form.yearly_income) : undefined,
    filing_status: form.filing_status,
    other_deductions: form.other_deductions,
    risk_appetite: form.risk_appetite,
    zip_code: form.zip_code || null,
    house_price: form.house_price ? Number(form.house_price) : null,
    down_payment_pct: form.down_payment_pct / 100,
    closing_cost_pct: form.closing_cost_pct / 100,
    maintenance_rate: form.maintenance_rate / 100,
    insurance_annual: form.insurance_annual,
    sell_cost_pct: form.sell_cost_pct / 100,
    move_in_cost: form.move_in_cost,
    mortgage_rate: form.mortgage_rate ? Number(form.mortgage_rate) / 100 : null,
    term_years: form.term_years,
    credit_quality: form.credit_quality,
    years: form.years,
    stay_years: form.stay_years === form.years ? null : form.stay_years,
    num_simulations: form.num_simulations,
    buy_delay_months: form.buy_delay_months,
    outlook_preset: form.outlook_preset,
    housing_crash_prob: form.housing_crash_prob,
    housing_crash_drop: form.housing_crash_drop,
    housing_recovery_pct: form.housing_recovery_pct,
    housing_recovery_months: form.housing_recovery_months,
    stock_crash_prob: form.stock_crash_prob,
    stock_crash_drop: form.stock_crash_drop,
    stock_recovery_pct: form.stock_recovery_pct,
    stock_recovery_months: form.stock_recovery_months,
    rate_target: form.rate_target ? Number(form.rate_target) / 100 : null,
    rate_volatility_scale: form.rate_volatility_scale !== "1.0" ? Number(form.rate_volatility_scale) : null,
  };
}

export async function postSummary(form: FormData): Promise<SummaryResponse> {
  const body = formToRequest(form);

  let res: Response;
  try {
    res = await fetch(`${API_URL}/summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error(
      `Cannot reach API at ${API_URL}. Make sure the backend is running: cd api && uvicorn api:app --reload`
    );
  }

  if (!res.ok) {
    const text = await res.text();
    // Parse structured validation errors from the API
    try {
      const json = JSON.parse(text);
      if (json.detail && Array.isArray(json.detail)) {
        const messages = json.detail.map((d: { message?: string }) => d.message).filter(Boolean);
        if (messages.length > 0) {
          throw new Error(messages.join("\n"));
        }
      }
    } catch (e) {
      if (e instanceof Error && !e.message.startsWith("API error")) throw e;
    }
    throw new Error(`API error ${res.status}: ${text}`);
  }

  return res.json();
}

// --- PRO: Analysis Endpoints ---

export async function postWhatIf(inputs: SummaryRequest): Promise<WhatIfResponse> {
  const res = await fetch(`${API_URL}/whatif`, {
    method: "POST",
    headers: proHeaders(),
    body: JSON.stringify(inputs),
  });
  if (!res.ok) throw new Error(`What-If analysis failed: ${res.status}`);
  return res.json();
}

export async function postSensitivity(inputs: SummaryRequest): Promise<SensitivityResponse> {
  const res = await fetch(`${API_URL}/sensitivity`, {
    method: "POST",
    headers: proHeaders(),
    body: JSON.stringify(inputs),
  });
  if (!res.ok) throw new Error(`Sensitivity analysis failed: ${res.status}`);
  return res.json();
}

export async function postTrend(inputs: SummaryRequest, maxDelayQuarters = 8): Promise<TrendResponse> {
  const res = await fetch(`${API_URL}/trend`, {
    method: "POST",
    headers: proHeaders(),
    body: JSON.stringify({ ...inputs, max_delay_quarters: maxDelayQuarters }),
  });
  if (!res.ok) throw new Error(`Trend analysis failed: ${res.status}`);
  return res.json();
}

export async function postLlmSummary(inputs: SummaryRequest): Promise<LlmSummaryResponse> {
  const res = await fetch(`${API_URL}/llm-summary`, {
    method: "POST",
    headers: proHeaders(),
    body: JSON.stringify(inputs),
  });
  if (!res.ok) throw new Error(`AI summary failed: ${res.status}`);
  return res.json();
}

// --- PRO: CSV Export ---

export async function downloadCsv(form: FormData): Promise<void> {
  const body = formToRequest(form);
  const res = await fetch(`${API_URL}/summary/csv`, {
    method: "POST",
    headers: proHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`CSV export failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "rent-vs-buy.csv";
  a.click();
  URL.revokeObjectURL(url);
}

// --- PRO: Device Email ---

export async function registerEmail(email: string): Promise<void> {
  const res = await fetch(`${API_URL}/devices/email`, {
    method: "POST",
    headers: proHeaders(),
    body: JSON.stringify({ email }),
  });
  if (!res.ok) throw new Error(`Failed to register email: ${res.status}`);
}

// --- PRO: Scenarios ---

export async function saveScenario(
  name: string,
  inputs: SummaryRequest,
  response?: SummaryResponse | null,
): Promise<Scenario> {
  const res = await fetch(`${API_URL}/scenarios`, {
    method: "POST",
    headers: proHeaders(),
    body: JSON.stringify({ name, inputs, response: response ?? null }),
  });
  if (!res.ok) throw new Error(`Failed to save scenario: ${res.status}`);
  return res.json();
}

export async function listScenarios(): Promise<Scenario[]> {
  const res = await fetch(`${API_URL}/scenarios`, { headers: proHeaders() });
  if (!res.ok) throw new Error(`Failed to list scenarios: ${res.status}`);
  const data: ScenarioList = await res.json();
  return data.scenarios;
}

export async function getScenario(id: string): Promise<Scenario> {
  const res = await fetch(`${API_URL}/scenarios/${id}`, { headers: proHeaders() });
  if (!res.ok) throw new Error(`Scenario not found: ${res.status}`);
  return res.json();
}

export async function runScenario(id: string): Promise<SummaryResponse> {
  const res = await fetch(`${API_URL}/scenarios/${id}/run`, {
    method: "POST",
    headers: proHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to re-run scenario: ${res.status}`);
  return res.json();
}

export async function deleteScenario(id: string): Promise<void> {
  const res = await fetch(`${API_URL}/scenarios/${id}`, {
    method: "DELETE",
    headers: proHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to delete scenario: ${res.status}`);
}

// --- PRO: Alerts ---

export async function addAlert(
  scenarioId: string,
  alertType: "threshold" | "shift" | "digest",
  config?: { shift_months?: number },
): Promise<Alert> {
  const res = await fetch(`${API_URL}/scenarios/${scenarioId}/alerts`, {
    method: "POST",
    headers: proHeaders(),
    body: JSON.stringify({ alert_type: alertType, config: config ?? null }),
  });
  if (res.status === 409) throw new Error("Alert type already exists for this scenario");
  if (!res.ok) throw new Error(`Failed to add alert: ${res.status}`);
  return res.json();
}

export async function listAlerts(scenarioId: string): Promise<Alert[]> {
  const res = await fetch(`${API_URL}/scenarios/${scenarioId}/alerts`, {
    headers: proHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to list alerts: ${res.status}`);
  const data: AlertList = await res.json();
  return data.alerts;
}

export async function deleteAlert(scenarioId: string, alertId: string): Promise<void> {
  const res = await fetch(`${API_URL}/scenarios/${scenarioId}/alerts/${alertId}`, {
    method: "DELETE",
    headers: proHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to delete alert: ${res.status}`);
}

export async function deleteAllAlerts(scenarioId: string): Promise<void> {
  const res = await fetch(`${API_URL}/scenarios/${scenarioId}/alerts`, {
    method: "DELETE",
    headers: proHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to delete alerts: ${res.status}`);
}
