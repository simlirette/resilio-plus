"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useRouter } from "next/navigation";
import {
  getLoadAnalytics,
  getSportBreakdown,
  getPerformanceAnalytics,
  type LoadAnalytics,
  type SportBreakdown,
  type PerformanceAnalytics,
} from "@/lib/api";
import { AcwrTrendChart } from "@/components/analytics/AcwrTrendChart";
import { TrainingLoadChart } from "@/components/analytics/TrainingLoadChart";
import { SportBreakdownChart } from "@/components/analytics/SportBreakdownChart";
import { PerformanceTrendChart } from "@/components/analytics/PerformanceTrendChart";

export default function AnalyticsPage() {
  const { athleteId, token } = useAuth();
  const router = useRouter();

  const [load, setLoad] = useState<LoadAnalytics | null>(null);
  const [breakdown, setBreakdown] = useState<SportBreakdown | null>(null);
  const [performance, setPerformance] = useState<PerformanceAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }
    if (!athleteId) return;

    Promise.all([
      getLoadAnalytics(athleteId),
      getSportBreakdown(athleteId),
      getPerformanceAnalytics(athleteId),
    ])
      .then(([l, b, p]) => {
        setLoad(l);
        setBreakdown(b);
        setPerformance(p);
      })
      .catch((e: Error) => setError(e.message ?? "Failed to load analytics"));
  }, [athleteId, token, router]);

  if (!token || !athleteId) return null;

  if (error) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-8">
        <p className="text-destructive">{error}</p>
      </main>
    );
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <h1 className="text-2xl font-bold">Analytics</h1>

      {/* ACWR */}
      <section className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold mb-1">ACWR Trend</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Acute:Chronic Workload Ratio — safe zone 0.8–1.3
        </p>
        {load ? (
          <AcwrTrendChart data={load.acwr} />
        ) : (
          <div className="h-48 animate-pulse bg-muted rounded" />
        )}
      </section>

      {/* Training Load */}
      <section className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold mb-1">Training Load</h2>
        <p className="text-sm text-muted-foreground mb-4">
          CTL (fitness), ATL (fatigue), TSB (form)
        </p>
        {load ? (
          <TrainingLoadChart data={load.training_load} />
        ) : (
          <div className="h-48 animate-pulse bg-muted rounded" />
        )}
      </section>

      {/* Sport Breakdown */}
      <section className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold mb-1">Sport Breakdown</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Total training hours per sport (all time)
        </p>
        {breakdown ? (
          <SportBreakdownChart data={breakdown} />
        ) : (
          <div className="h-48 animate-pulse bg-muted rounded" />
        )}
      </section>

      {/* Performance Trends */}
      <section className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold mb-1">Performance Trends</h2>
        <p className="text-sm text-muted-foreground mb-4">
          VDOT progression (running) and e1RM progression (lifting)
        </p>
        {performance ? (
          <PerformanceTrendChart data={performance} />
        ) : (
          <div className="h-48 animate-pulse bg-muted rounded" />
        )}
      </section>
    </main>
  );
}
