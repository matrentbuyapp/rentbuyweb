"use client";

import ProBadge from "./ProBadge";

interface Props {
  isPro: boolean;
  label: string;
  children: React.ReactNode;
}

/** Shows children for Pro users, a locked label for free users */
export default function ProGate({ isPro, label, children }: Props) {
  if (isPro) return <>{children}</>;
  return (
    <div className="flex items-center gap-1.5 py-1.5">
      <ProBadge />
      <span className="text-[11px] text-gray-400">{label}</span>
    </div>
  );
}
