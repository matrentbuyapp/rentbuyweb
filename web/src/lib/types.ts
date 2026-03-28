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
  num_simulations?: number;
  buy_delay_months?: number;
  crash_outlook?: string;
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

export interface SummaryResponse {
  house_price: number;
  mortgage_rate: number;
  property_tax_rate: number;
  avg_buyer_net_worth: number;
  avg_renter_net_worth: number;
  monthly: MonthlyData[];
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
  num_simulations: number;
  buy_delay_months: number;
  crash_outlook: string;
}
