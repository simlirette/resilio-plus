// frontend/src/components/top-nav.tsx
'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useTheme } from 'next-themes'
import { useAuth } from '@/lib/auth'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Icon } from '@resilio/ui-web'

const BASE_NAV_LINKS = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/energy', label: 'Energy' },
  { href: '/check-in', label: 'Check-in' },
  { href: '/plan', label: 'Plan' },
  { href: '/review', label: 'Review' },
  { href: '/history', label: 'History' },
  { href: '/analytics', label: 'Analytics' },
  { href: '/settings/connectors', label: 'Settings' },
]

const TRACKING_LINK = { href: '/tracking', label: 'Tracking' }

export function TopNav() {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const { token, logout, coachingMode } = useAuth()

  const navLinks = coachingMode === 'tracking_only'
    ? [...BASE_NAV_LINKS, TRACKING_LINK]
    : BASE_NAV_LINKS

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-14 max-w-screen-xl items-center gap-6 px-4">
        <Link href="/" className="flex items-center gap-2 font-bold tracking-widest text-primary">
          RESILIO+
          {coachingMode === 'tracking_only' && (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-semibold tracking-wider border-amber-500 text-amber-500">
              TRACKING
            </Badge>
          )}
        </Link>

        {token && (
          <nav className="hidden gap-6 md:flex">
            {navLinks.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className={`text-sm font-medium transition-colors hover:text-primary ${
                  pathname === href || pathname.startsWith(href + '/')
                    ? 'text-foreground border-b-2 border-primary pb-0.5'
                    : 'text-muted-foreground'
                }`}
              >
                {label}
              </Link>
            ))}
          </nav>
        )}

        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label="Toggle theme"
          >
            <Icon.LightMode className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Icon.DarkMode className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          </Button>
          {token && (
            <Button variant="ghost" size="sm" onClick={logout}>
              Logout
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
