"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { clearToken, getFirstName } from "@/lib/api";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const firstName = getFirstName();

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  function linkClass(href: string) {
    const active =
      href === "/dashboard"
        ? pathname === "/dashboard"
        : pathname.startsWith(href);
    return `px-3 py-1 rounded text-sm transition-colors ${
      active
        ? "bg-violet-600 text-white"
        : "text-slate-400 hover:text-slate-100"
    }`;
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between h-14 px-6 bg-slate-900 border-b border-slate-800">
      <span className="font-bold text-violet-400 tracking-tight">Resilio+</span>

      <div className="flex items-center gap-2">
        <Link href="/dashboard" className={linkClass("/dashboard")}>
          Dashboard
        </Link>
        <Link href="/dashboard/calendar" className={linkClass("/dashboard/calendar")}>
          Calendrier
        </Link>
        <Link href="/dashboard/weekly-review" className={linkClass("/dashboard/weekly-review")}>
          Bilan
        </Link>
        <Link href="/dashboard/chat" className={linkClass("/dashboard/chat")}>
          Chat
        </Link>
        <Link href="/dashboard/settings" className={linkClass("/dashboard/settings")}>
          Paramètres
        </Link>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-400">{firstName}</span>
        <button
          onClick={handleLogout}
          className="px-3 py-1 text-sm rounded bg-slate-800 text-slate-300 hover:bg-slate-700 transition-colors"
        >
          Déconnexion
        </button>
      </div>
    </nav>
  );
}
