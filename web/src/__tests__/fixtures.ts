import { SummaryResponse, SummaryRequest, FormData, Scenario, MonthlyData } from "@/lib/types";
import { DEFAULT_FORM_VALUES } from "@/lib/defaults";

function makeMonthly(months: number): MonthlyData[] {
  return Array.from({ length: months }, (_, i) => ({
    home_value: 300000 + i * 500,
    mortgage_payment: 1800,
    interest_payment: 1200,
    principal_payment: 600,
    remaining_balance: 240000 - i * 600,
    maintenance: 250,
    property_tax: 300,
    insurance: 150,
    pmi: i < 60 ? 80 : 0,
    tax_savings: 200,
    total_housing_cost: 2380,
    rent: 1800 + i * 5,
    budget: 2500,
    buyer_investment: 10000 + i * 120,
    renter_investment: 50000 + i * 700,
    buyer_equity: 60000 + i * 1100,
    buyer_net_worth: 70000 + i * 1220,
    renter_net_worth: 50000 + i * 700,
    cumulative_buy_cost: 2380 * (i + 1),
    cumulative_rent_cost: (1800 + i * 2.5) * (i + 1),
  }));
}

export const MOCK_RESULT: SummaryResponse = {
  headline: {
    winner: "buy",
    short: "You'd be $47K richer buying after 10 years",
    detail: "Buying costs more monthly but equity growth makes up for it.",
    confidence: "high",
    monthly_savings: 500,
  },
  house_price: 300000,
  mortgage_rate: 0.065,
  property_tax_rate: 0.012,
  avg_buyer_net_worth: 217400,
  avg_renter_net_worth: 134000,
  buy_score: 72,
  verdict: "Lean Buy",
  breakeven_month: 54,
  crossing_count: 1,
  monthly: makeMonthly(120),
  percentiles: {
    buyer_net_worth: { p10: [], p25: [], p50: [], p75: [], p90: [] },
    renter_net_worth: { p10: [], p25: [], p50: [], p75: [], p90: [] },
    home_value: { p10: [], p25: [], p50: [], p75: [], p90: [] },
    buyer_equity: { p10: [], p25: [], p50: [], p75: [], p90: [] },
    mortgage_rate: { p10: [], p25: [], p50: [], p75: [], p90: [] },
  },
  warnings: [],
};

export const MOCK_REQUEST: SummaryRequest = {
  monthly_rent: 1800,
  monthly_budget: 2500,
  initial_cash: 60000,
  years: 10,
};

export const MOCK_FORM: FormData = { ...DEFAULT_FORM_VALUES };

export const MOCK_SCENARIO: Scenario = {
  id: "scenario-1",
  name: "Test Downtown",
  inputs: MOCK_REQUEST,
  response: MOCK_RESULT,
  cache_key: "abc123",
  data_vintage: "2026-03-30",
  created_at: Date.now() / 1000,
  updated_at: Date.now() / 1000,
};

export const MOCK_SCENARIO_2: Scenario = {
  id: "scenario-2",
  name: "Test Suburbs",
  inputs: { ...MOCK_REQUEST, monthly_rent: 1500 },
  response: { ...MOCK_RESULT, house_price: 250000, verdict: "Strong Buy", buy_score: 88 },
  cache_key: "def456",
  data_vintage: "2026-03-30",
  created_at: Date.now() / 1000 - 3600,
  updated_at: Date.now() / 1000 - 3600,
};
