"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

interface AthleteMe {
  id: string;
  email: string;
  first_name: string;
}

interface StravaStatus {
  connected: boolean;
  last_sync: string | null;
  token_expires_at: string | null;
}

interface HevyStatus {
  connected: boolean;
  last_sync: string | null;
}

function Badge({ connected }: { connected: boolean }) {
  return connected ? (
    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-emerald-900 text-emerald-200">
      Connecté
    </span>
  ) : (
    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-400">
      Non connecté
    </span>
  );
}

function LastSync({ date }: { date: string | null }) {
  if (!date) return null;
  const formatted = new Date(date).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <p className="text-xs text-slate-500 mt-1">
      Dernière sync&nbsp;: {formatted}
    </p>
  );
}

export default function SettingsPage() {
  const router = useRouter();

  const [athleteId, setAthleteId] = useState<string | null>(null);
  const [stravaStatus, setStravaStatus] = useState<StravaStatus | null>(null);
  const [hevyStatus, setHevyStatus] = useState<HevyStatus | null>(null);
  const [hevyKey, setHevyKey] = useState("");
  const [hevyError, setHevyError] = useState("");
  const [hevySuccess, setHevySuccess] = useState(false);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");

  // Strava action states
  const [stravaConnecting, setStravaConnecting] = useState(false);
  const [stravaDisconnecting, setStravaDisconnecting] = useState(false);

  // Hevy action states
  const [hevyConnecting, setHevyConnecting] = useState(false);
  const [hevyDisconnecting, setHevyDisconnecting] = useState(false);

  function authHeader(): Record<string, string> {
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("resilio_token")
        : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function fetchStatuses(id: string) {
    const [strava, hevy] = await Promise.all([
      api.get<StravaStatus>(`/connectors/strava/status?athlete_id=${id}`),
      api.get<HevyStatus>(`/connectors/hevy/status?athlete_id=${id}`),
    ]);
    setStravaStatus(strava);
    setHevyStatus(hevy);
  }

  useEffect(() => {
    api
      .get<AthleteMe>("/athletes/me")
      .then(async (me) => {
        setAthleteId(me.id);
        await fetchStatuses(me.id);
      })
      .catch((err: Error & { status?: number }) => {
        if (err?.status === 401) {
          router.replace("/login");
        } else {
          setPageError(err.message);
        }
      })
      .finally(() => setLoading(false));
  }, [router]);

  async function handleStravaConnect() {
    if (!athleteId) return;
    setStravaConnecting(true);
    try {
      const { authorization_url } = await api.get<{ authorization_url: string }>(
        "/connectors/strava/auth"
      );
      window.location.href = authorization_url;
    } catch (err) {
      console.error(err);
    } finally {
      setStravaConnecting(false);
    }
  }

  async function handleStravaDisconnect() {
    if (!athleteId) return;
    setStravaDisconnecting(true);
    try {
      await fetch(
        `${BASE_URL}/connectors/strava/disconnect?athlete_id=${athleteId}`,
        { method: "DELETE", headers: authHeader() }
      );
      await fetchStatuses(athleteId);
    } catch (err) {
      console.error(err);
    } finally {
      setStravaDisconnecting(false);
    }
  }

  async function handleHevyConnect() {
    if (!athleteId) return;
    setHevyError("");
    setHevySuccess(false);
    setHevyConnecting(true);
    try {
      await api.post<{ connected: true }>(
        `/connectors/hevy/connect?athlete_id=${athleteId}`,
        { api_key: hevyKey }
      );
      setHevySuccess(true);
      setHevyKey("");
      await fetchStatuses(athleteId);
    } catch (err) {
      setHevyError("Clé API Hevy invalide.");
    } finally {
      setHevyConnecting(false);
    }
  }

  async function handleHevyDisconnect() {
    if (!athleteId) return;
    setHevyDisconnecting(true);
    setHevySuccess(false);
    try {
      await fetch(
        `${BASE_URL}/connectors/hevy/disconnect?athlete_id=${athleteId}`,
        { method: "DELETE", headers: authHeader() }
      );
      await fetchStatuses(athleteId);
    } catch (err) {
      console.error(err);
    } finally {
      setHevyDisconnecting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 text-sm">Chargement...</div>
      </div>
    );
  }

  if (pageError) {
    return <p className="text-red-400 text-sm">{pageError}</p>;
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-slate-100">Paramètres</h2>

      {/* Strava */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-5 space-y-4">
        <div className="flex items-center gap-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Strava
          </h3>
          {stravaStatus && <Badge connected={stravaStatus.connected} />}
        </div>

        {stravaStatus?.connected && (
          <LastSync date={stravaStatus.last_sync} />
        )}

        <div className="flex gap-3">
          {!stravaStatus?.connected ? (
            <button
              onClick={handleStravaConnect}
              disabled={stravaConnecting}
              className="px-4 py-2 text-sm rounded bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white transition-colors"
            >
              {stravaConnecting ? "Redirection…" : "Connecter Strava"}
            </button>
          ) : (
            <button
              onClick={handleStravaDisconnect}
              disabled={stravaDisconnecting}
              className="px-4 py-2 text-sm rounded bg-red-800 hover:bg-red-700 disabled:opacity-50 text-white transition-colors"
            >
              {stravaDisconnecting ? "Déconnexion…" : "Déconnecter"}
            </button>
          )}
        </div>
      </div>

      {/* Hevy */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-5 space-y-4">
        <div className="flex items-center gap-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Hevy
          </h3>
          {hevyStatus && <Badge connected={hevyStatus.connected} />}
        </div>

        {hevyStatus?.connected && <LastSync date={hevyStatus.last_sync} />}

        {!hevyStatus?.connected ? (
          <div className="space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={hevyKey}
                onChange={(e) => {
                  setHevyKey(e.target.value);
                  setHevyError("");
                  setHevySuccess(false);
                }}
                placeholder="Clé API Hevy"
                className="flex-1 px-3 py-2 text-sm rounded bg-slate-800 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
              <button
                onClick={handleHevyConnect}
                disabled={hevyConnecting || !hevyKey.trim()}
                className="px-4 py-2 text-sm rounded bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white transition-colors"
              >
                {hevyConnecting ? "Connexion…" : "Connecter"}
              </button>
            </div>
            {hevySuccess && (
              <p className="text-sm text-emerald-400">Hevy connecté ✓</p>
            )}
            {hevyError && (
              <p className="text-sm text-red-400">{hevyError}</p>
            )}
          </div>
        ) : (
          <div className="flex gap-3">
            <button
              onClick={handleHevyDisconnect}
              disabled={hevyDisconnecting}
              className="px-4 py-2 text-sm rounded bg-red-800 hover:bg-red-700 disabled:opacity-50 text-white transition-colors"
            >
              {hevyDisconnecting ? "Déconnexion…" : "Déconnecter"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
