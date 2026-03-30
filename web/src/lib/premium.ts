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
    id: "whatif",
    title: "What-If Scenarios",
    description: "What if rates drop? What if you wait? See how common changes would affect your outcome.",
    endpoint: "/whatif",
  },
  {
    id: "sensitivity",
    title: "Sensitivity Analysis",
    description: "Which inputs matter most for your decision? Interactive heatmap included.",
    endpoint: "/sensitivity",
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
  {
    id: "buying-memo",
    title: "Export Buying Memo",
    description: "Download a personalized PDF with your numbers — ready to share with your lender or agent.",
    endpoint: "/buying-memo",
  },
];
