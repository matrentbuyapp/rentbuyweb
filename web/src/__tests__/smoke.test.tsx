/**
 * Smoke tests — every component renders without crashing.
 * Fast, wide coverage. No API calls.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MOCK_RESULT, MOCK_FORM, MOCK_SCENARIO, MOCK_SCENARIO_2 } from "./fixtures";

// --- Lib ---
import { formatCurrency, formatPercent, formatCompact } from "@/lib/formatters";
import { DEFAULT_FORM_VALUES } from "@/lib/defaults";
import { formToRequest } from "@/lib/api";

describe("Lib: formatters", () => {
  it("formatCurrency", () => {
    expect(formatCurrency(1234)).toBe("$1,234");
    expect(formatCurrency(-500)).toBe("-$500");
    expect(formatCurrency(0)).toBe("$0");
  });
  it("formatPercent", () => {
    expect(formatPercent(0.065)).toBe("6.50%");
  });
  it("formatCompact", () => {
    expect(formatCompact(1500000)).toBe("$1.5M");
    expect(formatCompact(250000)).toBe("$250K");
    expect(formatCompact(500)).toBe("$500");
  });
});

describe("Lib: defaults", () => {
  it("has required fields", () => {
    expect(DEFAULT_FORM_VALUES.monthly_rent).toBe(1800);
    expect(DEFAULT_FORM_VALUES.years).toBe(10);
    expect(DEFAULT_FORM_VALUES.stay_years).toBe(10);
    expect(DEFAULT_FORM_VALUES.outlook_preset).toBe("historical");
    expect(DEFAULT_FORM_VALUES.yearly_income).toBe("");
  });
});

describe("Lib: formToRequest", () => {
  it("converts percentages to decimals", () => {
    const req = formToRequest(MOCK_FORM);
    expect(req.down_payment_pct).toBe(0.08);
    expect(req.closing_cost_pct).toBe(0.03);
    expect(req.maintenance_rate).toBe(0.01);
  });
  it("sends null for empty optional fields", () => {
    const req = formToRequest(MOCK_FORM);
    expect(req.house_price).toBeNull();
    expect(req.mortgage_rate).toBeNull();
    expect(req.zip_code).toBeNull();
  });
  it("sends stay_years as null when equal to years", () => {
    const req = formToRequest({ ...MOCK_FORM, stay_years: 10, years: 10 });
    expect(req.stay_years).toBeNull();
  });
  it("sends stay_years when different from years", () => {
    const req = formToRequest({ ...MOCK_FORM, stay_years: 5, years: 10 });
    expect(req.stay_years).toBe(5);
  });
});

// --- UI Primitives ---
import ProBadge from "@/components/ui/ProBadge";
import QuickStats from "@/components/ui/QuickStats";
import ViewSwitcher from "@/components/ui/ViewSwitcher";
import ProGate from "@/components/ui/ProGate";

describe("UI: ProBadge", () => {
  it("renders", () => {
    const { container } = render(<ProBadge />);
    expect(container.textContent).toContain("PRO");
  });
});

describe("UI: QuickStats", () => {
  it("renders with full result", () => {
    render(<QuickStats result={MOCK_RESULT} />);
    expect(screen.getByText(/\$300,000/)).toBeInTheDocument();
  });
  it("handles result with empty monthly", () => {
    const partial = { ...MOCK_RESULT, monthly: [] };
    const { container } = render(<QuickStats result={partial} />);
    expect(container).toBeTruthy();
  });
});

describe("UI: ViewSwitcher", () => {
  it("renders live state", () => {
    render(
      <ViewSwitcher activeScenario={null} scenarios={[]} hasLive={true}
        onSelectLive={() => {}} onSelectScenario={() => {}} />
    );
    expect(screen.getByText("Live")).toBeInTheDocument();
  });
  it("renders scenario state", () => {
    render(
      <ViewSwitcher activeScenario={MOCK_SCENARIO} scenarios={[MOCK_SCENARIO]} hasLive={true}
        onSelectLive={() => {}} onSelectScenario={() => {}} />
    );
    expect(screen.getByText("Test Downtown")).toBeInTheDocument();
  });
  it("renders compact mode", () => {
    const { container } = render(
      <ViewSwitcher activeScenario={null} scenarios={[]} hasLive={true}
        onSelectLive={() => {}} onSelectScenario={() => {}} compact />
    );
    expect(container).toBeTruthy();
  });
});

describe("UI: ProGate", () => {
  it("shows children for pro", () => {
    render(<ProGate isPro={true} label="test"><span>content</span></ProGate>);
    expect(screen.getByText("content")).toBeInTheDocument();
  });
  it("shows label for free", () => {
    render(<ProGate isPro={false} label="Unlock this"><span>content</span></ProGate>);
    expect(screen.getByText("Unlock this")).toBeInTheDocument();
    expect(screen.queryByText("content")).not.toBeInTheDocument();
  });
});

// --- Result Components ---
import KeyMetrics from "@/components/results/KeyMetrics";
import ResultsDashboard from "@/components/results/ResultsDashboard";
import ChartCard from "@/components/results/ChartCard";

describe("Results: KeyMetrics", () => {
  it("renders with headline", () => {
    render(<KeyMetrics data={MOCK_RESULT} />);
    expect(screen.getByText(/\$47K richer/)).toBeInTheDocument();
  });
  it("renders without headline (fallback)", () => {
    const noHeadline = { ...MOCK_RESULT, headline: undefined };
    render(<KeyMetrics data={noHeadline} />);
    expect(screen.getByText(/better off buying/)).toBeInTheDocument();
  });
  it("renders pro detail row when isPro", () => {
    render(<KeyMetrics data={MOCK_RESULT} isPro />);
    expect(screen.getByText("72/100")).toBeInTheDocument();
    expect(screen.getByText("Lean Buy")).toBeInTheDocument();
  });
  it("hides pro row when not isPro", () => {
    render(<KeyMetrics data={MOCK_RESULT} />);
    expect(screen.queryByText("72/100")).not.toBeInTheDocument();
  });
  it("handles toss-up (crossing_count >= 4)", () => {
    const tossup = { ...MOCK_RESULT, crossing_count: 5, breakeven_month: null };
    render(<KeyMetrics data={tossup} />);
    expect(screen.getByText("Toss-up")).toBeInTheDocument();
  });
  it("handles renter wins", () => {
    const renterWins = {
      ...MOCK_RESULT,
      headline: { ...MOCK_RESULT.headline!, winner: "rent" as const, short: "Renting saves you $20K" },
      avg_buyer_net_worth: 100000,
      avg_renter_net_worth: 120000,
    };
    render(<KeyMetrics data={renterWins} />);
    expect(screen.getByText(/Renting saves/)).toBeInTheDocument();
  });
});

describe("Results: ResultsDashboard", () => {
  it("renders null when no result", () => {
    const { container } = render(
      <ResultsDashboard result={null} loading={false} error={null} isPro={false} />
    );
    expect(container.innerHTML).toBe("");
  });
  it("renders loading state", () => {
    render(<ResultsDashboard result={null} loading={true} error={null} isPro={false} />);
    expect(screen.getByText(/500 simulations/)).toBeInTheDocument();
  });
  it("renders error state", () => {
    render(<ResultsDashboard result={null} loading={false} error="Something broke" isPro={false} />);
    expect(screen.getByText("Something broke")).toBeInTheDocument();
  });
  it("renders validation errors with bullet points", () => {
    render(<ResultsDashboard result={null} loading={false}
      error={"Not enough savings\nMortgage too high"} isPro={false} />);
    expect(screen.getByText("Not enough savings")).toBeInTheDocument();
    expect(screen.getByText("Mortgage too high")).toBeInTheDocument();
  });
  it("renders with full result", () => {
    const { container } = render(
      <ResultsDashboard result={MOCK_RESULT} loading={false} error={null} isPro={false} />
    );
    expect(container.querySelector("[class*=recharts]") || container.innerHTML.length > 100).toBeTruthy();
  });
  it("renders warnings", () => {
    const withWarnings = { ...MOCK_RESULT, warnings: [{ code: "dti", message: "DTI is 48%", severity: "warning" }] };
    render(<ResultsDashboard result={withWarnings} loading={false} error={null} isPro={false} />);
    expect(screen.getByText("DTI is 48%")).toBeInTheDocument();
  });
});

describe("Results: ChartCard", () => {
  it("renders with title", () => {
    render(<ChartCard title="Test Chart"><div>chart</div></ChartCard>);
    expect(screen.getByText("Test Chart")).toBeInTheDocument();
  });
});

// --- Charts (smoke only — render without crash) ---
import NetWorthChart from "@/components/results/NetWorthChart";
import HomeValueChart from "@/components/results/HomeValueChart";
import RentVsBuyChart from "@/components/results/RentVsBuyChart";
import CostBreakdownChart from "@/components/results/CostBreakdownChart";

describe("Charts: smoke render", () => {
  const monthly = MOCK_RESULT.monthly.slice(0, 12); // small set for speed

  it("NetWorthChart", () => {
    const { container } = render(<NetWorthChart monthly={monthly} />);
    expect(container).toBeTruthy();
  });
  it("NetWorthChart with breakeven and sell", () => {
    const { container } = render(<NetWorthChart monthly={monthly} breakevenMonth={6} sellMonth={10} />);
    expect(container).toBeTruthy();
  });
  it("HomeValueChart", () => {
    const { container } = render(<HomeValueChart monthly={monthly} />);
    expect(container).toBeTruthy();
  });
  it("RentVsBuyChart", () => {
    const { container } = render(<RentVsBuyChart monthly={monthly} />);
    expect(container).toBeTruthy();
  });
  it("CostBreakdownChart", () => {
    const { container } = render(<CostBreakdownChart monthly={monthly} />);
    expect(container).toBeTruthy();
  });
  it("CostBreakdownChart with sell line", () => {
    const { container } = render(<CostBreakdownChart monthly={monthly} sellMonth={8} />);
    expect(container).toBeTruthy();
  });
});

// --- Form Components ---
import CrashSlider from "@/components/form/CrashSlider";
import DownPaymentInput from "@/components/form/DownPaymentInput";

describe("Form: CrashSlider", () => {
  it("renders all presets", () => {
    render(<CrashSlider value="historical" onChange={() => {}} />);
    expect(screen.getByText("Historical")).toBeInTheDocument();
    expect(screen.getByText("Optimistic")).toBeInTheDocument();
    expect(screen.getByText("Crisis")).toBeInTheDocument();
  });
});

describe("Form: DownPaymentInput", () => {
  it("renders with basic props", () => {
    render(
      <DownPaymentInput pct={10} onPctChange={() => {}} homePrice={300000}
        savings={60000} closingPct={3} moveInCost={0} />
    );
    expect(screen.getByText(/savings left/)).toBeInTheDocument();
  });
  it("shows short when over budget", () => {
    render(
      <DownPaymentInput pct={50} onPctChange={() => {}} homePrice={300000}
        savings={60000} closingPct={3} moveInCost={0} />
    );
    expect(screen.getByText(/short/)).toBeInTheDocument();
  });
  it("shows PMI warning under 20%", () => {
    render(
      <DownPaymentInput pct={10} onPctChange={() => {}} homePrice={300000}
        savings={60000} closingPct={3} moveInCost={0} />
    );
    expect(screen.getByText(/PMI/)).toBeInTheDocument();
  });
  it("no PMI at 20%+", () => {
    render(
      <DownPaymentInput pct={20} onPctChange={() => {}} homePrice={300000}
        savings={100000} closingPct={3} moveInCost={0} />
    );
    expect(screen.getByText(/no PMI/)).toBeInTheDocument();
  });
});

// --- Scenario Components ---
import SaveButton from "@/components/scenarios/SaveButton";
import ScenarioList from "@/components/scenarios/ScenarioList";

describe("Scenarios: SaveButton", () => {
  it("renders initial state", () => {
    render(<SaveButton inputs={{} as any} response={MOCK_RESULT} onSave={async () => {}} />);
    expect(screen.getByText("Save Scenario")).toBeInTheDocument();
  });
});

describe("Scenarios: ScenarioList", () => {
  it("renders empty state", () => {
    render(<ScenarioList scenarios={[]} loading={false} onRerun={async () => MOCK_RESULT}
      onDelete={async () => {}} onViewResult={() => {}} />);
    expect(screen.getByText(/No saved scenarios/)).toBeInTheDocument();
  });
  it("renders loading state", () => {
    render(<ScenarioList scenarios={[]} loading={true} onRerun={async () => MOCK_RESULT}
      onDelete={async () => {}} onViewResult={() => {}} />);
    expect(screen.getByText(/Loading/)).toBeInTheDocument();
  });
  it("renders scenarios", () => {
    render(<ScenarioList scenarios={[MOCK_SCENARIO, MOCK_SCENARIO_2]} loading={false}
      onRerun={async () => MOCK_RESULT} onDelete={async () => {}} onViewResult={() => {}} />);
    expect(screen.getByText("Test Downtown")).toBeInTheDocument();
    expect(screen.getByText("Test Suburbs")).toBeInTheDocument();
  });
});

// --- Pro Insights Components ---
import WhatIfSection from "@/components/insights/WhatIfSection";
import SensitivitySection from "@/components/insights/SensitivitySection";
import TrendSection from "@/components/insights/TrendSection";
import LlmSummarySection from "@/components/insights/LlmSummarySection";

describe("Insights: WhatIfSection", () => {
  it("renders load button when no data", () => {
    render(<WhatIfSection data={null} loading={false} onLoad={() => {}} />);
    expect(screen.getByText(/Run What-If/)).toBeInTheDocument();
  });
  it("renders loading", () => {
    render(<WhatIfSection data={null} loading={true} onLoad={() => {}} />);
    expect(screen.getByText(/Running scenarios/)).toBeInTheDocument();
  });
  it("renders with data", () => {
    const data = {
      base_net_diff: 50000,
      scenarios: [
        { id: "test", name: "Test Scenario", description: "desc", buyer_net_worth: 200000,
          renter_net_worth: 150000, net_difference: 50000, delta_from_base: 0,
          breakeven_month: 30, buy_score: 80 },
      ],
    };
    render(<WhatIfSection data={data} loading={false} onLoad={() => {}} />);
    expect(screen.getByText("Test Scenario")).toBeInTheDocument();
  });
});

describe("Insights: TrendSection", () => {
  it("renders load button when no data", () => {
    render(<TrendSection data={null} loading={false} onLoad={() => {}} />);
    expect(screen.getByText(/Run Timing/)).toBeInTheDocument();
  });
  it("renders with data", () => {
    const data = {
      points: [
        { delay_months: 0, aggregate_score: 60, mortgage_rate_used: 0.065,
          buyer_net_worth: 200000, renter_net_worth: 150000, net_difference: 50000, breakeven_month: 30 },
        { delay_months: 6, aggregate_score: 70, mortgage_rate_used: 0.06,
          buyer_net_worth: 210000, renter_net_worth: 150000, net_difference: 60000, breakeven_month: 24 },
      ],
    };
    render(<TrendSection data={data} loading={false} onLoad={() => {}} />);
    expect(screen.getByText("Now")).toBeInTheDocument();
    expect(screen.getByText("+6mo")).toBeInTheDocument();
  });
});

describe("Insights: LlmSummarySection", () => {
  it("renders load button when no data", () => {
    render(<LlmSummarySection data={null} loading={false} onLoad={() => {}} />);
    expect(screen.getByText(/Generate AI Summary/)).toBeInTheDocument();
  });
  it("renders with data", () => {
    const data = {
      summary: "Buying is favorable.", buy_costs_summary: "Costs are high.",
      buy_pros: ["Equity growth"], rent_pros: ["Flexibility"],
      buy_costs: ["High upfront"], rent_costs: ["No equity"],
      verdict: "Lean Buy", score: 72,
    };
    render(<LlmSummarySection data={data} loading={false} onLoad={() => {}} />);
    expect(screen.getByText("Buying is favorable.")).toBeInTheDocument();
    expect(screen.getByText("Equity growth")).toBeInTheDocument();
  });
});

describe("Insights: SensitivitySection", () => {
  it("renders load button when no data", () => {
    render(<SensitivitySection data={null} loading={false} onLoad={() => {}} />);
    expect(screen.getByText(/Run Sensitivity/)).toBeInTheDocument();
  });
});

// --- Device & Storage ---
import { getDeviceId } from "@/lib/device";
import { storeResult, loadResult } from "@/lib/resultStore";

describe("Lib: device", () => {
  it("returns consistent ID", () => {
    const id1 = getDeviceId();
    const id2 = getDeviceId();
    expect(id1).toBe(id2);
  });
});

describe("Lib: resultStore", () => {
  it("stores and loads", () => {
    storeResult(MOCK_RESULT, { monthly_rent: 1800, monthly_budget: 2500 });
    const loaded = loadResult();
    expect(loaded).not.toBeNull();
    expect(loaded!.result.house_price).toBe(300000);
  });
  it("stores scenario context", () => {
    storeResult(MOCK_RESULT, { monthly_rent: 1800, monthly_budget: 2500 }, { id: "s1", name: "My Test" });
    const loaded = loadResult();
    expect(loaded!.scenario_name).toBe("My Test");
  });
});
