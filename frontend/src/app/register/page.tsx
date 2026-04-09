"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";

interface RegisterResponse {
  id: string;
  email: string;
  first_name: string;
  access_token: string;
}

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    age: "",
    sex: "M",
    weight_kg: "",
    height_cm: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api.post<RegisterResponse>("/auth/register", {
        ...form,
        age: parseInt(form.age, 10),
        weight_kg: parseFloat(form.weight_kg),
        height_cm: parseFloat(form.height_cm),
      });
      setToken(data.access_token, data.first_name);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur d'inscription");
    } finally {
      setLoading(false);
    }
  }

  const inputClass =
    "w-full px-3 py-2 rounded bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-violet-500";
  const labelClass = "block text-sm text-slate-400 mb-1";

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4 py-10">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold text-violet-400 mb-2">Resilio+</h1>
        <p className="text-slate-400 text-sm mb-8">Créer votre profil athlète</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={labelClass}>Prénom</label>
            <input
              type="text"
              value={form.first_name}
              onChange={(e) => update("first_name", e.target.value)}
              required
              className={inputClass}
              placeholder="Simon"
            />
          </div>
          <div>
            <label className={labelClass}>Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
              required
              className={inputClass}
              placeholder="simon@example.com"
            />
          </div>
          <div>
            <label className={labelClass}>Mot de passe</label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              required
              className={inputClass}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Âge</label>
              <input
                type="number"
                value={form.age}
                onChange={(e) => update("age", e.target.value)}
                required
                min="16"
                max="80"
                className={inputClass}
                placeholder="32"
              />
            </div>
            <div>
              <label className={labelClass}>Sexe</label>
              <select
                value={form.sex}
                onChange={(e) => update("sex", e.target.value)}
                className={inputClass}
              >
                <option value="M">Homme</option>
                <option value="F">Femme</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Poids (kg)</label>
              <input
                type="number"
                value={form.weight_kg}
                onChange={(e) => update("weight_kg", e.target.value)}
                required
                step="0.1"
                className={inputClass}
                placeholder="78.5"
              />
            </div>
            <div>
              <label className={labelClass}>Taille (cm)</label>
              <input
                type="number"
                value={form.height_cm}
                onChange={(e) => update("height_cm", e.target.value)}
                required
                className={inputClass}
                placeholder="178"
              />
            </div>
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white font-medium transition-colors"
          >
            {loading ? "Création..." : "Créer mon compte"}
          </button>
        </form>

        <p className="mt-6 text-sm text-slate-400 text-center">
          Déjà un compte ?{" "}
          <Link href="/login" className="text-violet-400 hover:underline">
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}
