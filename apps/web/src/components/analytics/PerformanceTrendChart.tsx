"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { PerformanceAnalytics } from "@/lib/api";

interface Props {
  data: PerformanceAnalytics;
}

export function PerformanceTrendChart({ data }: Props) {
  const hasVdot = data.vdot.length > 0;
  const hasE1rm = data.e1rm.length > 0;

  if (!hasVdot && !hasE1rm) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
        No performance data yet — log sessions with VDOT or e1RM
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {hasVdot && (
        <div>
          <p className="text-sm font-medium text-muted-foreground mb-1">VDOT (Running)</p>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={data.vdot} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
              <Tooltip formatter={(val) => (typeof val === "number" ? val.toFixed(1) : String(val))} />
              <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} name="VDOT" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
      {hasE1rm && (
        <div>
          <p className="text-sm font-medium text-muted-foreground mb-1">e1RM (Lifting, kg)</p>
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={data.e1rm} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
              <Tooltip formatter={(val) => (typeof val === "number" ? `${val.toFixed(1)} kg` : String(val))} />
              <Line type="monotone" dataKey="value" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} name="e1RM" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
