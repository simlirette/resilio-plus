// frontend/src/app/tracking/import/page.tsx
'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, type ExternalPlanDraft } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

type Step = 'upload' | 'preview' | 'confirmed'

const SPORT_LABELS: Record<string, string> = {
  running: 'Course',
  lifting: 'Musculation',
  swimming: 'Natation',
  biking: 'Vélo',
}

function formatDate(iso: string | null): string {
  if (!iso) return 'Date inconnue'
  return new Date(iso).toLocaleDateString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' })
}

export default function TrackingImportPage() {
  const { athleteId, coachingMode } = useAuth()
  const router = useRouter()
  const fileRef = useRef<HTMLInputElement>(null)
  const [step, setStep] = useState<Step>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [draft, setDraft] = useState<ExternalPlanDraft | null>(null)
  const [loading, setLoading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (coachingMode !== null && coachingMode !== 'tracking_only') {
      router.replace('/dashboard')
    }
  }, [coachingMode, router])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) setFile(dropped)
  }, [])

  async function analyse() {
    if (!athleteId || !file) return
    setLoading(true)
    setError('')
    try {
      const result = await api.importExternalPlan(athleteId, file)
      setDraft(result)
      setStep('preview')
    } catch {
      setError("Erreur lors de l'analyse. Réessayez.")
    } finally {
      setLoading(false)
    }
  }

  async function confirm() {
    if (!athleteId || !draft) return
    setLoading(true)
    setError('')
    try {
      await api.confirmImportExternalPlan(athleteId, draft)
      setStep('confirmed')
    } catch {
      setError('Erreur lors de la confirmation.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ProtectedRoute>
      <div className="space-y-6 max-w-2xl">
        <div className="flex items-center gap-3">
          <Link href="/tracking" className="text-sm text-muted-foreground hover:text-foreground">
            ← Plan externe
          </Link>
          <span className="text-muted-foreground">/</span>
          <span className="text-sm font-medium">Importer</span>
        </div>

        <div>
          <h1 className="text-2xl font-bold">Importer un plan</h1>
          <p className="text-sm text-muted-foreground mt-1">PDF, TXT, CSV ou ICS</p>
        </div>

        {step === 'upload' && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Étape 1 — Choisir un fichier</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                onDragOver={e => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileRef.current?.click()}
                className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
                  dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-muted-foreground/50'
                }`}
              >
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.txt,.csv,.ics"
                  className="hidden"
                  onChange={e => setFile(e.target.files?.[0] ?? null)}
                />
                {file ? (
                  <div>
                    <p className="text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-muted-foreground mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm text-muted-foreground">Glissez un fichier ici ou cliquez pour sélectionner</p>
                    <p className="text-xs text-muted-foreground mt-1">PDF · TXT · CSV · ICS</p>
                  </div>
                )}
              </div>

              {error && <p className="text-sm text-destructive">{error}</p>}

              <Button onClick={analyse} disabled={!file || loading}>
                {loading ? 'Analyse en cours…' : 'Analyser avec IA'}
              </Button>
            </CardContent>
          </Card>
        )}

        {step === 'preview' && draft && (
          <Card>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-base">Étape 2 — Vérifier le plan détecté</CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    {draft.sessions_parsed} séance{draft.sessions_parsed !== 1 ? 's' : ''} détectée{draft.sessions_parsed !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {draft.parse_warnings.length > 0 && (
                <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 px-3 py-2 space-y-1">
                  {draft.parse_warnings.map((w, i) => (
                    <p key={i} className="text-xs text-yellow-600 dark:text-yellow-400">{w}</p>
                  ))}
                </div>
              )}

              <div className="divide-y">
                {draft.sessions.map((s, i) => (
                  <div key={i} className="flex items-center gap-3 py-3">
                    <div className="w-24 text-xs text-muted-foreground shrink-0">{formatDate(s.session_date)}</div>
                    <Badge variant="outline" className="text-xs shrink-0">
                      {SPORT_LABELS[s.sport] ?? s.sport}
                    </Badge>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{s.title}</p>
                      {s.duration_min && (
                        <p className="text-xs text-muted-foreground">{s.duration_min} min</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {error && <p className="text-sm text-destructive">{error}</p>}

              <div className="flex gap-2 pt-2">
                <Button onClick={confirm} disabled={loading}>
                  {loading ? 'Confirmation…' : "Confirmer l'import"}
                </Button>
                <Button variant="ghost" onClick={() => { setStep('upload'); setDraft(null); setFile(null) }}>
                  ← Retour
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 'confirmed' && (
          <Card>
            <CardContent className="py-10 text-center space-y-4">
              <p className="text-4xl">✓</p>
              <p className="text-lg font-semibold">Plan importé !</p>
              <p className="text-sm text-muted-foreground">Vos séances ont été ajoutées à votre plan externe.</p>
              <Button asChild>
                <Link href="/tracking">Voir mon plan →</Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </ProtectedRoute>
  )
}
