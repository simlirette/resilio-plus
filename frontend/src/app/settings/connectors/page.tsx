'use client'
import { useEffect, useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError } from '@/lib/api'
import { ProtectedRoute } from '@/components/protected-route'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

type ConnectorStatus = {
  provider: string
  connected: boolean
  expires_at?: number | null
  last_sync?: string | null
}
type SyncResult = { message: string; ok: boolean }

function formatLastSync(lastSync?: string | null): string {
  if (!lastSync) return 'Never synced'
  const d = new Date(lastSync)
  return d.toLocaleString()
}

export default function ConnectorsPage() {
  const { athleteId, logout } = useAuth()
  const router = useRouter()
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState<string | null>(null)
  const [results, setResults] = useState<Record<string, SyncResult>>({})
  const [hevyKey, setHevyKey] = useState('')
  const [terraUserId, setTerraUserId] = useState('')
  const [connecting, setConnecting] = useState<string | null>(null)
  const [disconnecting, setDisconnecting] = useState<string | null>(null)
  const gpxRef = useRef<HTMLInputElement>(null)
  const fitRef = useRef<HTMLInputElement>(null)

  const reload = () => {
    if (!athleteId) return
    api.getConnectors(athleteId)
      .then(data => setConnectors(data.connectors))
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
      })
  }

  useEffect(() => {
    if (!athleteId) return
    api.getConnectors(athleteId)
      .then(data => setConnectors(data.connectors))
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) { logout(); router.replace('/login') }
      })
      .finally(() => setLoading(false))
  }, [athleteId, logout, router])

  const getConnector = (provider: string): ConnectorStatus | undefined =>
    connectors.find(c => c.provider === provider)

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
      reload()
    } catch {
      setResults(r => ({ ...r, [provider]: { ok: false, message: 'Sync failed' } }))
    } finally {
      setSyncing(null)
    }
  }

  const connectHevy = async () => {
    if (!athleteId || !hevyKey.trim()) return
    setConnecting('hevy')
    try {
      await api.connectHevy(athleteId, hevyKey.trim())
      setHevyKey('')
      setResults(r => ({ ...r, hevy: { ok: true, message: 'Connected' } }))
      reload()
    } catch {
      setResults(r => ({ ...r, hevy: { ok: false, message: 'Connection failed' } }))
    } finally {
      setConnecting(null)
    }
  }

  const connectTerra = async () => {
    if (!athleteId || !terraUserId.trim()) return
    setConnecting('terra')
    try {
      await api.connectTerraUserId(athleteId, terraUserId.trim())
      setTerraUserId('')
      setResults(r => ({ ...r, terra: { ok: true, message: 'Connected' } }))
      reload()
    } catch {
      setResults(r => ({ ...r, terra: { ok: false, message: 'Connection failed' } }))
    } finally {
      setConnecting(null)
    }
  }

  const disconnect = async (provider: 'strava' | 'hevy' | 'terra') => {
    if (!athleteId) return
    setDisconnecting(provider)
    try {
      await api.disconnectConnector(athleteId, provider)
      setResults(r => ({ ...r, [provider]: { ok: true, message: 'Disconnected' } }))
      reload()
    } catch {
      setResults(r => ({ ...r, [provider]: { ok: false, message: 'Disconnect failed' } }))
    } finally {
      setDisconnecting(null)
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
          <CardContent className="space-y-2">
            {isConnected('strava') && (
              <p className="text-xs text-muted-foreground">
                Last sync: {formatLastSync(getConnector('strava')?.last_sync)}
              </p>
            )}
            <div className="flex gap-2 flex-wrap">
              {!isConnected('strava') && athleteId && (
                <Button variant="outline" size="sm" onClick={() =>
                  api.stravaAuthorize(athleteId).then(d => window.location.href = d.auth_url)
                }>Connect</Button>
              )}
              {isConnected('strava') && (
                <>
                  <Button variant="outline" size="sm" disabled={syncing === 'strava'}
                    onClick={() => syncConnector('strava', () => api.stravaSync(athleteId!))}>
                    {syncing === 'strava' ? 'Syncing…' : 'Sync now'}
                  </Button>
                  <Button variant="ghost" size="sm" disabled={disconnecting === 'strava'}
                    className="text-destructive hover:text-destructive"
                    onClick={() => disconnect('strava')}>
                    {disconnecting === 'strava' ? 'Disconnecting…' : 'Disconnect'}
                  </Button>
                </>
              )}
              {results.strava && (
                <span className={`text-xs self-center ${results.strava.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                  {results.strava.message}
                </span>
              )}
            </div>
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
          <CardContent className="space-y-2">
            {isConnected('hevy') && (
              <p className="text-xs text-muted-foreground">
                Last sync: {formatLastSync(getConnector('hevy')?.last_sync)}
              </p>
            )}
            {!isConnected('hevy') && (
              <div className="flex gap-2">
                <Input
                  placeholder="Hevy API key"
                  value={hevyKey}
                  onChange={e => setHevyKey(e.target.value)}
                  className="h-8 text-sm max-w-xs"
                  type="password"
                />
                <Button variant="outline" size="sm" disabled={connecting === 'hevy' || !hevyKey.trim()}
                  onClick={connectHevy}>
                  {connecting === 'hevy' ? 'Connecting…' : 'Connect'}
                </Button>
              </div>
            )}
            <div className="flex gap-2 flex-wrap">
              {isConnected('hevy') && (
                <>
                  <Button variant="outline" size="sm" disabled={syncing === 'hevy'}
                    onClick={() => syncConnector('hevy', () => api.hevySync(athleteId!))}>
                    {syncing === 'hevy' ? 'Syncing…' : 'Sync now'}
                  </Button>
                  <Button variant="ghost" size="sm" disabled={disconnecting === 'hevy'}
                    className="text-destructive hover:text-destructive"
                    onClick={() => disconnect('hevy')}>
                    {disconnecting === 'hevy' ? 'Disconnecting…' : 'Disconnect'}
                  </Button>
                </>
              )}
              {results.hevy && (
                <span className={`text-xs self-center ${results.hevy.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                  {results.hevy.message}
                </span>
              )}
            </div>
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
          <CardContent className="space-y-2">
            {isConnected('terra') && (
              <p className="text-xs text-muted-foreground">
                Last sync: {formatLastSync(getConnector('terra')?.last_sync)}
              </p>
            )}
            {!isConnected('terra') && (
              <div className="flex gap-2">
                <Input
                  placeholder="Terra user ID"
                  value={terraUserId}
                  onChange={e => setTerraUserId(e.target.value)}
                  className="h-8 text-sm max-w-xs"
                />
                <Button variant="outline" size="sm" disabled={connecting === 'terra' || !terraUserId.trim()}
                  onClick={connectTerra}>
                  {connecting === 'terra' ? 'Connecting…' : 'Connect'}
                </Button>
              </div>
            )}
            <div className="flex gap-2 flex-wrap">
              {isConnected('terra') && (
                <>
                  <Button variant="outline" size="sm" disabled={syncing === 'terra'}
                    onClick={() => syncConnector('terra', () => api.terraSync(athleteId!))}>
                    {syncing === 'terra' ? 'Syncing…' : 'Sync now'}
                  </Button>
                  <Button variant="ghost" size="sm" disabled={disconnecting === 'terra'}
                    className="text-destructive hover:text-destructive"
                    onClick={() => disconnect('terra')}>
                    {disconnecting === 'terra' ? 'Disconnecting…' : 'Disconnect'}
                  </Button>
                </>
              )}
              {results.terra && (
                <span className={`text-xs self-center ${results.terra.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                  {results.terra.message}
                </span>
              )}
            </div>
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
