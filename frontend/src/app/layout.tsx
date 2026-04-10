// frontend/src/app/layout.tsx
import type { Metadata } from 'next'
import { ThemeProvider } from 'next-themes'
import { AuthProvider } from '@/lib/auth'
import { TopNav } from '@/components/top-nav'
import './globals.css'

export const metadata: Metadata = {
  title: 'Resilio+',
  description: 'AI-powered hybrid athlete coaching',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <AuthProvider>
            <TopNav />
            <main className="mx-auto max-w-screen-xl px-4 py-8">
              {children}
            </main>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
