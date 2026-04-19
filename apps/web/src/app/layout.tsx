// frontend/src/app/layout.tsx
import type { Metadata } from 'next'
import { Space_Grotesk, Space_Mono } from 'next/font/google'
import { ThemeProvider } from '@resilio/ui-web'
import { AuthProvider } from '@/lib/auth'
import { TopNav } from '@/components/top-nav'
import './globals.css'

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700'],
  variable: '--font-space-grotesk',
})

const spaceMono = Space_Mono({
  subsets: ['latin'],
  weight: ['400', '700'],
  variable: '--font-space-mono',
})

export const metadata: Metadata = {
  title: 'Resilio+',
  description: 'AI-powered hybrid athlete coaching',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${spaceGrotesk.variable} ${spaceMono.variable}`}>
      <body>
        <ThemeProvider>
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
