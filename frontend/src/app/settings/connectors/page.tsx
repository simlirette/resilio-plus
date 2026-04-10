'use client'
import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

type ConnectorStatus = { provider: string; connected: boolean; expires_at?: number | null }
type SyncResult = { message: string; ok: boolean }

export default function ConnectorsPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, SyncResult>>({})
  const gpxRef = useRef<HTMLInputElement>(null)
  const fitRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!athleteId) return
    api.getConnectors(athleteId)
      .then(data => setConnectors(data.connectors))
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
      })
      .finally(() => setLoading(false))
  }, [athleteId, logout, router])

  const isConnected = (provider: string) =>
    connectors.some(c => c.provider === provider && c.connected)

  const syncConnector = async (provider: string, action: () => Promise<any>) => {
    if (!athleteId) return
    setSyncing(provider)
    try {
      const result = await action()
      setResults(r => ({
        ...r,
        [provider]: { ok: true, message: `Synced ${result.synced ?? 1} item(s)` },
      }))
    } catch {
      setResults(r => ({ ...r, [provider]: { ok: false, message: 'Sync failed' } }))
    } finally {
      setSyncing(null)
    }
  }

  const handleFileUpload = async (
    provider: 'gpx' | 'fit',
    file: File | null | undefined
  ) => {
    if (!file || !athleteId) return
    setSyncing(provider)
    try {
      const result = provider === 'gpx'
        ? await api.uploadGpx(athleteId, file)
        : await api.uploadFit(athleteId, file)
      setResults(r => ({
        ...r,
        [provider]: {
          ok: result.imported,
          message: result.imported
            ? `Imported → session ${result.session_id}`
            : `Not imported: ${(result as any).reason}`,
        },
      }))
    } catch {
      setResults(r => ({ ...r, [provider]: { ok: false, message: 'Upload failed' } }))
    } finally {
      setSyncing(null)
    }
  }

  return (
    <ProtectedRoute>
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">Connected Apps</h1>
        {loading && <p className="animate-pulse text-muted-foreground">Loading…</p>}

        {/* Strava */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Strava</CardTitle>
              <span className={`text-xs px-2 py-0.5 rounded-full ${isConnected('strava') ? 'bg-emerald-500/20 text-emerald-400' : 'bg-muted text-muted-foreground'}`}>
                {isConnected('strava') ? 'Connected' : 'Not connected'}
              </span>
            </div>
          </CardHeader>
          <CardContent className="flex gap-2 flex-wrap">
            {!isConnected('strava') && athleteId && (
              <Button variant="outline" size="sm" onClick={() =>
                api.stravaAuthorize(athleteId).then(d => window.location.href = d.auth_url)
              }>Connect</Button>
            )}
            {isConnected('strava') && (
              <Button variant="outline" size="sm" disabled={syncing === 'strava'}
                onClick={() => syncConnector('strava', () => api.stravaSync(athleteId!))}>
                {syncing === 'strava' ? 'Syncing…' : 'Sync now'}
              </Button>
            )}
            {results.strava && (
              <span className={`text-xs self-center ${results.strava.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                {results.strava.message}
              </span>
            )}
          </CardContent>
        </Card>

        {/* Hevy */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Hevy</CardTitle>
              <span className={`text-xs px-2 py-0.5 rounded-full ${isConnected('hevy') ? 'bg-purple-500/20 text-purple-400' : 'bg-muted text-muted-foreground'}`}>
                {isConnected('hevy') ? 'Connected' : 'Not connected'}
              </span>
            </div>
          </CardHeader>
          <CardContent className="flex gap-2 flex-wrap">
            {isConnected('hevy') && (
              <Button variant="outline" size="sm" disabled={syncing === 'hevy'}
                onClick={() => syncConnector('hevy', () => api.hevySync(athleteId!))}>
                {syncing === 'hevy' ? 'Syncing…' : 'Sync now'}
              </Button>
            )}
            {results.hevy && (
              <span className={`text-xs self-center ${results.hevy.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                {results.hevy.message}
              </span>
            )}
          </CardContent>
        </Card>

        {/* Terra */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Terra (HRV / Sleep)</CardTitle>
              <span className={`text-xs px-2 py-0.5 rounded-full ${isConnected('terra') ? 'bg-blue-500/20 text-blue-400' : 'bg-muted text-muted-foreground'}`}>
                {isConnected('terra') ? 'Connected' : 'Not connected'}
              </span>
            </div>
          </CardHeader>
          <CardContent className="flex gap-2 flex-wrap">
            {isConnected('terra') && (
              <Button variant="outline" size="sm" disabled={syncing === 'terra'}
                onClick={() => syncConnector('terra', () => api.terraSync(athleteId!))}>
                {syncing === 'terra' ? 'Syncing…' : 'Sync now'}
              </Button>
            )}
            {results.terra && (
              <span className={`text-xs self-center ${results.terra.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                {results.terra.message}
              </span>
            )}
          </CardContent>
        </Card>

        {/* Apple Health */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Apple Health</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground mb-2">
              Upload HRV and sleep data from Apple Health JSON export.
            </p>
            <p className="text-xs text-muted-foreground">
              Use the Apple Health export → share as JSON → paste HRV/sleep values below.
            </p>
          </CardContent>
        </Card>

        {/* GPX / FIT */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Import Activity File</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="text-xs text-muted-foreground mb-2">GPX file (GPS track)</p>
              <input ref={gpxRef} type="file" accept=".gpx" className="hidden"
                onChange={e => handleFileUpload('gpx', e.target.files?.[0])} />
              <Button variant="outline" size="sm" disabled={syncing === 'gpx'}
                onClick={() => gpxRef.current?.click()}>
                {syncing === 'gpx' ? 'Importing…' : 'Upload GPX'}
              </Button>
              {results.gpx && (
                <span className={`text-xs ml-2 ${results.gpx.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                  {results.gpx.message}
                </span>
              )}
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-2">FIT file (Garmin / Wahoo)</p>
              <input ref={fitRef} type="file" accept=".fit" className="hidden"
                onChange={e => handleFileUpload('fit', e.target.files?.[0])} />
              <Button variant="outline" size="sm" disabled={syncing === 'fit'}
                onClick={() => fitRef.current?.click()}>
                {syncing === 'fit' ? 'Importing…' : 'Upload FIT'}
              </Button>
              {results.fit && (
                <span className={`text-xs ml-2 ${results.fit.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                  {results.fit.message}
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </ProtectedRoute>
  )
}
