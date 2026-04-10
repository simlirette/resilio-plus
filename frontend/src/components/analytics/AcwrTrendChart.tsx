"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { AcwrPoint } from "@/lib/api";

interface Props {
  data: AcwrPoint[];
}

export function AcwrTrendChart({ data }: Props) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        No data yet — log sessions to see ACWR trend
      </div>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    date: d.date.slice(5), // "MM-DD"
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={formatted} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11 }}
          interval="preserveStartEnd"
        />
        <YAxis domain={[0, 2]} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(val) => (typeof val === "number" ? val.toFixed(2) : String(val))}
          labelFormatter={(label) => `Date: ${label}`}
        />
        {/* Safe zone */}
        <ReferenceLine y={0.8} stroke="#22c55e" strokeDasharray="4 4" label={{ value: "0.8", position: "right", fontSize: 10 }} />
        <ReferenceLine y={1.3} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: "1.3", position: "right", fontSize: 10 }} />
        <ReferenceLine y={1.5} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "1.5", position: "right", fontSize: 10 }} />
        <Line
          type="monotone"
          dataKey="acwr"
          stroke="var(--primary)"
          strokeWidth={2}
          dot={false}
          name="ACWR"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
