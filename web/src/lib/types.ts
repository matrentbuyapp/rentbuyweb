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
  // Refinance
  refi_enabled?: boolean;
  refi_threshold?: number | null;
  refi_closing_cost?: number | null;
  refi_max_count?: number | null;
  refi_min_months?: number | null;
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

export interface Headline {
  winner: "buy" | "rent" | "toss-up";
  short: string;
  detail: string;
  confidence: "high" | "moderate" | "low";
  monthly_savings: number;
}

export interface RefiSummary {
  pct_sims_refinanced: number;
  avg_refi_month: number;
  avg_refi_rate: number;
  avg_payment_drop: number;
  avg_total_savings: number;
  no_refi_buyer_net_worth: number;
  refi_benefit: number;
}

export interface SummaryResponse {
  headline?: Headline;
  house_price: number;
  mortgage_rate: number;
  property_tax_rate: number;
  avg_buyer_net_worth: number;
  avg_renter_net_worth: number;
  buy_score: number;
  verdict: string;
  breakeven_month: number | null;
  crossing_count: number;
  cache_key?: string;
  data_vintage?: string;
  monthly: MonthlyData[];
  percentiles: Percentiles;
  refi_summary?: RefiSummary | null;
  warnings?: Warning[];
}

// --- PRO: Saved Scenarios & Alerts ---

export interface Scenario {
  id: string;
  name: string;
  inputs: SummaryRequest;
  response: SummaryResponse | null;
  cache_key: string | null;
  data_vintage: string | null;
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

// --- Pro Analysis Response Types ---

export interface WhatIfScenario {
  id: string;
  name: string;
  description: string;
  buyer_net_worth: number;
  renter_net_worth: number;
  net_difference: number;
  delta_from_base: number;
  breakeven_month: number | null;
  buy_score: number;
}

export interface WhatIfResponse {
  base_net_diff: number;
  scenarios: WhatIfScenario[];
}

export interface SensitivityPoint {
  label: string;
  param_name: string;
  param_value: number;
  buyer_net_worth: number;
  renter_net_worth: number;
  net_difference: number;
  breakeven_month: number | null;
}

export interface HeatmapCell {
  x_label: string;
  y_label: string;
  x_value: number;
  y_value: number;
  net_difference: number;
  breakeven_month: number | null;
  buy_score: number;
}

export interface SensitivityResponse {
  base_buyer_nw: number;
  base_renter_nw: number;
  base_net_diff: number;
  base_buy_score: number;
  axes: Record<string, SensitivityPoint[]>;
  heatmap: {
    x_axis: string;
    y_axis: string;
    x_labels: string[];
    y_labels: string[];
    cells: HeatmapCell[][];  // cells[y_idx][x_idx]
  };
}

export interface TrendPoint {
  delay_months: number;
  aggregate_score: number;
  mortgage_rate_used: number;
  buyer_net_worth: number;
  renter_net_worth: number;
  net_difference: number;
  delta_from_now?: number;
  breakeven_month: number | null;
}

export interface TrendResponse {
  points: TrendPoint[];
}

export interface LlmSummaryResponse {
  summary: string;
  buy_costs_summary: string;
  buy_pros: string[];
  rent_pros: string[];
  buy_costs: string[];
  rent_costs: string[];
  verdict: string;
  score: number;
}

export interface FormData {
  monthly_rent: number;
  monthly_budget: number;
  initial_cash: number;
  yearly_income: string;
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
  // Refinance (Pro overrides, on by default)
  refi_enabled: boolean;
  refi_threshold: number | null;
  refi_closing_cost: number | null;
  refi_max_count: number | null;
  refi_min_months: number | null;
}
