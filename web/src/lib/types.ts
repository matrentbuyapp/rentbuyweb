export interface SummaryRequest {
  monthly_rent: number;
  monthly_budget: number;
  initial_cash?: number;
  yearly_income?: number;
  filing_status?: string;
  other_deductions?: number;
  risk_appetite?: string;
  zip_code?: string | null;
  house_price?: number | null;
  down_payment_pct?: number;
  closing_cost_pct?: number;
  maintenance_rate?: number;
  insurance_annual?: number;
  sell_cost_pct?: number;
  move_in_cost?: number;
  mortgage_rate?: number | null;
  term_years?: number;
  credit_quality?: string;
  years?: number;
  stay_years?: number | null;
  num_simulations?: number;
  buy_delay_months?: number;
  outlook_preset?: string;
  // Pro outlook overrides
  volatility_scale?: number | null;
  housing_crash_prob?: number | null;
  housing_crash_drop?: number | null;
  housing_drawdown_months?: number | null;
  housing_recovery_pct?: number | null;
  housing_recovery_months?: number | null;
  stock_crash_prob?: number | null;
  stock_crash_drop?: number | null;
  stock_drawdown_months?: number | null;
  stock_recovery_pct?: number | null;
  stock_recovery_months?: number | null;
  // Pro rate forecast overrides
  rate_target?: number | null;
  rate_volatility_scale?: number | null;
}

export interface MonthlyData {
  home_value: number;
  mortgage_payment: number;
  interest_payment: number;
  principal_payment: number;
  remaining_balance: number;
  maintenance: number;
  property_tax: number;
  insurance: number;
  pmi: number;
  tax_savings: number;
  total_housing_cost: number;
  rent: number;
  budget: number;
  buyer_investment: number;
  renter_investment: number;
  buyer_equity: number;
  buyer_net_worth: number;
  renter_net_worth: number;
  cumulative_buy_cost: number;
  cumulative_rent_cost: number;
}

export interface PercentileBands {
  p10: number[];
  p25: number[];
  p50: number[];
  p75: number[];
  p90: number[];
}

export interface Percentiles {
  buyer_net_worth: PercentileBands;
  renter_net_worth: PercentileBands;
  home_value: PercentileBands;
  buyer_equity: PercentileBands;
  mortgage_rate: PercentileBands;
}

export interface Warning {
  code: string;
  severity?: string;
  message: string;
}

export interface SummaryResponse {
  house_price: number;
  mortgage_rate: number;
  property_tax_rate: number;
  avg_buyer_net_worth: number;
  avg_renter_net_worth: number;
  buy_score: number;
  verdict: string;
  breakeven_month: number | null;
  crossing_count: number;
  monthly: MonthlyData[];
  percentiles: Percentiles;
  warnings?: Warning[];
}

// --- PRO: Saved Scenarios & Alerts ---

export interface Scenario {
  id: string;
  name: string;
  inputs: SummaryRequest;
  response: SummaryResponse | null;
  created_at: number;
  updated_at: number;
}

export interface ScenarioList {
  scenarios: Scenario[];
}

export interface Alert {
  id: string;
  scenario_id: string;
  alert_type: "threshold" | "shift" | "digest";
  enabled: boolean;
  config: { shift_months?: number } | null;
  last_triggered_at: number | null;
  created_at: number;
}

export interface AlertList {
  alerts: Alert[];
}

export interface FormData {
  monthly_rent: number;
  monthly_budget: number;
  initial_cash: number;
  yearly_income: number;
  filing_status: string;
  other_deductions: number;
  risk_appetite: string;
  zip_code: string;
  house_price: string;
  down_payment_pct: number;
  closing_cost_pct: number;
  maintenance_rate: number;
  insurance_annual: number;
  sell_cost_pct: number;
  move_in_cost: number;
  mortgage_rate: string;
  term_years: number;
  credit_quality: string;
  years: number;
  stay_years: number;
  num_simulations: number;
  buy_delay_months: number;
  outlook_preset: string;
  // Pro crash overrides (null = use preset defaults)
  housing_crash_prob: number | null;
  housing_crash_drop: number | null;
  housing_recovery_pct: number | null;
  housing_recovery_months: number | null;
  stock_crash_prob: number | null;
  stock_crash_drop: number | null;
  stock_recovery_pct: number | null;
  stock_recovery_months: number | null;
  // Pro rate forecast overrides
  rate_target: string;
  rate_volatility_scale: string;
}
