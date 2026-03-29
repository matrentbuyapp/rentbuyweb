export interface ProFeature {
  id: string;
  title: string;
  description: string;
  endpoint: string;
}

export const PRO_FEATURES: ProFeature[] = [
  {
    id: "ai-summary",
    title: "AI-Powered Summary",
    description: "A plain-English analysis of your situation with personalized pros and cons for buying vs renting.",
    endpoint: "/llm-summary",
  },
  {
    id: "buying-memo",
    title: "Export Buying Memo",
    description: "Download a personalized PDF with your numbers, market data, and analysis — ready to share with your lender or agent.",
    endpoint: "/buying-memo",
  },
  {
    id: "sensitivity",
    title: "What-If Analysis",
    description: "See how changing your rate, price, or down payment would shift the outcome. Interactive heatmap included.",
    endpoint: "/sensitivity",
  },
  {
    id: "scenarios",
    title: "Save & Compare Scenarios",
    description: "Save different scenarios and compare them side by side. Get alerts when market changes affect your decision.",
    endpoint: "/scenarios",
  },
  {
    id: "trend",
    title: "Best Time to Buy",
    description: "Should you buy now or wait? See how delaying 3, 6, 12, or 24 months changes the picture.",
    endpoint: "/trend",
  },
  {
    id: "zip-compare",
    title: "Neighborhood Comparison",
    description: "Compare buying outcomes across nearby ZIP codes to find the best value.",
    endpoint: "/zip-compare",
  },
];
