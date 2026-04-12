"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { SportBreakdown } from "@/lib/api";

const COLORS: Record<string, string> = {
  running: "#6366f1",
  lifting: "#f59e0b",
  biking: "#22c55e",
  swimming: "#06b6d4",
  other: "#94a3b8",
};

interface Props {
  data: SportBreakdown;
}

export function SportBreakdownChart({ data }: Props) {
  const entries = Object.entries(data).map(([name, minutes]) => ({
    name,
    value: Math.round((minutes / 60) * 10) / 10, // hours, 1 decimal
  }));

  if (entries.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        No sessions logged yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={entries}
          cx="50%"
          cy="50%"
          outerRadius={80}
          dataKey="value"
          label={({ name, value }) => `${name} ${value}h`}
          labelLine={false}
        >
          {entries.map((entry) => (
            <Cell
              key={entry.name}
              fill={COLORS[entry.name] ?? COLORS.other}
            />
          ))}
        </Pie>
        <Tooltip formatter={(val) => [`${val}h`, "Hours"]} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}
