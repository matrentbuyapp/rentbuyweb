import { FormData, SummaryRequest, SummaryResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function postSummary(form: FormData): Promise<SummaryResponse> {
  const body: SummaryRequest = {
    monthly_rent: form.monthly_rent,
    monthly_budget: form.monthly_budget,
    initial_cash: form.initial_cash,
    yearly_income: form.yearly_income,
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
    num_simulations: form.num_simulations,
    buy_delay_months: form.buy_delay_months,
    crash_outlook: form.crash_outlook,
  };

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
    throw new Error(`API error ${res.status}: ${text}`);
  }

  return res.json();
}
