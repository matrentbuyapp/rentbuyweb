"use client";

interface Props {
  title: string;
  children: React.ReactNode;
}

export default function ChartCard({ title, children }: Props) {
  return (
    <div className="rounded-2xl border border-gray-100 bg-white/70 backdrop-blur-sm p-5 card-hover">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-4">{title}</h3>
      {children}
    </div>
  );
}
