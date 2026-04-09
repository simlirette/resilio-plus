"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface AthleteProfile {
  id: string;
  email: string;
  first_name: string;
  age: number;
  sex: string;
  weight_kg: number;
  height_cm: number;
  body_fat_percent: number | null;
  resting_hr: number | null;
  max_hr_measured: number | null;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-slate-400">{label}</span>
      <span className="text-slate-100">{value}</span>
    </div>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<AthleteProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<AthleteProfile>("/athletes/me")
      .then(setProfile)
      .catch((err: Error & { status?: number }) => {
        if (err?.status === 401) {
          router.replace("/login");
        } else {
          setError(err.message);
        }
      })
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 text-sm">Chargement...</div>
      </div>
    );
  }

  if (error) {
    return <p className="text-red-400 text-sm">{error}</p>;
  }

  if (!profile) return null;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-100">
        Bonjour, {profile.first_name}
      </h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-5 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Profil
          </h3>
          <div className="space-y-2">
            <Row label="Email" value={profile.email} />
            <Row label="Âge" value={`${profile.age} ans`} />
            <Row label="Sexe" value={profile.sex === "M" ? "Homme" : "Femme"} />
          </div>
        </div>

        <div className="bg-slate-900 rounded-lg border border-slate-800 p-5 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Mesures
          </h3>
          <div className="space-y-2">
            <Row label="Poids" value={`${profile.weight_kg} kg`} />
            <Row label="Taille" value={`${profile.height_cm} cm`} />
            {profile.body_fat_percent != null && (
              <Row label="Masse grasse" value={`${profile.body_fat_percent}%`} />
            )}
            {profile.resting_hr != null && (
              <Row label="FC repos" value={`${profile.resting_hr} bpm`} />
            )}
          </div>
        </div>
      </div>

      <div className="bg-slate-900 rounded-lg border border-slate-800 p-5">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">
          Navigation rapide
        </h3>
        <div className="flex gap-3">
          <a
            href="/dashboard/calendar"
            className="px-4 py-2 text-sm rounded bg-violet-600 hover:bg-violet-500 text-white transition-colors"
          >
            Voir mon calendrier
          </a>
          <a
            href="/dashboard/chat"
            className="px-4 py-2 text-sm rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            Chat Head Coach
          </a>
        </div>
      </div>
    </div>
  );
}
