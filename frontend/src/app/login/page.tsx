"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";

interface LoginResponse {
  access_token: string;
  token_type: string;
}

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api.post<LoginResponse>("/auth/login", { email, password });
      setToken(data.access_token, "");
      const me = await api.get<{ first_name: string }>("/athletes/me");
      setToken(data.access_token, me.first_name);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-violet-400 mb-2">Resilio+</h1>
        <p className="text-slate-400 text-sm mb-8">Connexion à votre espace athlète</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-violet-500"
              placeholder="simon@example.com"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Mot de passe</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-violet-500"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white font-medium transition-colors"
          >
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>

        <p className="mt-6 text-sm text-slate-400 text-center">
          Pas encore de compte ?{" "}
          <Link href="/register" className="text-violet-400 hover:underline">
            Créer un compte
          </Link>
        </p>
      </div>
    </div>
  );
}
