"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { TrainingLoadPoint } from "@/lib/api";

interface Props {
  data: TrainingLoadPoint[];
}

export function TrainingLoadChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        No data yet — log sessions to see training load
      </div>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    date: d.date.slice(5),
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={formatted} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={(val) => (typeof val === "number" ? val.toFixed(1) : String(val))} />
        <Legend />
        <Line type="monotone" dataKey="ctl" stroke="#6366f1" strokeWidth={2} dot={false} name="CTL" />
        <Line type="monotone" dataKey="atl" stroke="#f59e0b" strokeWidth={2} dot={false} name="ATL" />
        <Line type="monotone" dataKey="tsb" stroke="#22c55e" strokeWidth={1.5} dot={false} strokeDasharray="4 4" name="TSB" />
      </LineChart>
    </ResponsiveContainer>
  );
}
