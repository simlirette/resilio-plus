// frontend/src/app/onboarding/page.tsx
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth'
import { api, ApiError, type Sport } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'

const SPORTS: { value: Sport; label: string }[] = [
  { value: 'running', label: 'Running' },
  { value: 'lifting', label: 'Lifting' },
  { value: 'swimming', label: 'Swimming' },
  { value: 'biking', label: 'Biking' },
]

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function nextMonday(): string {
  const d = new Date()
  const day = d.getDay()
  const daysUntilMonday = day === 0 ? 1 : 8 - day
  d.setDate(d.getDate() + daysUntilMonday)
  return d.toISOString().split('T')[0]
}

interface FormData {
  // Step 1
  email: string
  password: string
  // Step 2
  name: string
  age: string
  sex: 'M' | 'F' | 'other'
  weight_kg: string
  height_cm: string
  primary_sport: Sport
  sports: Sport[]
  goals: string
  available_days: number[]
  hours_per_week: string
  // Step 3
  plan_start_date: string
}

const INITIAL: FormData = {
  email: '', password: '', name: '', age: '', sex: 'M',
  weight_kg: '', height_cm: '', primary_sport: 'running', sports: ['running'],
  goals: '', available_days: [0, 1, 2, 3, 4], hours_per_week: '',
  plan_start_date: nextMonday(),
}

export default function OnboardingPage() {
  const router = useRouter()
  const { login } = useAuth()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState<FormData>(INITIAL)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function set(key: keyof FormData, value: unknown) {
    setForm(f => ({ ...f, [key]: value }))
  }

  function toggleSport(sport: Sport) {
    set('sports', form.sports.includes(sport)
      ? form.sports.filter(s => s !== sport)
      : [...form.sports, sport])
  }

  function toggleDay(day: number) {
    set('available_days', form.available_days.includes(day)
      ? form.available_days.filter(d => d !== day)
      : [...form.available_days, day].sort())
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.onboarding({
        email: form.email,
        password: form.password,
        plan_start_date: form.plan_start_date,
        name: form.name,
        age: parseInt(form.age),
        sex: form.sex,
        weight_kg: parseFloat(form.weight_kg),
        height_cm: parseFloat(form.height_cm),
        primary_sport: form.primary_sport,
        sports: form.sports.length > 0 ? form.sports : [form.primary_sport],
        goals: form.goals.split(',').map(g => g.trim()).filter(Boolean),
        available_days: form.available_days,
        hours_per_week: parseFloat(form.hours_per_week),
      })
      login(res.access_token, res.athlete.id as string)
      router.replace('/dashboard')
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError('Email already in use. Sign in instead.')
      } else if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Something went wrong. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const stepTitles = ['Account', 'Athlete Profile', 'Your Plan']

  return (
    <div className="flex min-h-[80vh] items-center justify-center">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-2xl font-bold tracking-widest text-primary">RESILIO+</CardTitle>
          <CardDescription>Set up your coaching profile</CardDescription>
          {/* Step indicator */}
          <div className="flex items-center gap-2 pt-2">
            {[1, 2, 3].map(n => (
              <div key={n} className="flex items-center gap-2">
                <div className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                  step === n ? 'bg-primary text-primary-foreground' : step > n ? 'bg-primary/40 text-primary-foreground' : 'bg-muted text-muted-foreground'
                }`}>{n}</div>
                <span className={`text-xs ${step === n ? 'text-foreground font-medium' : 'text-muted-foreground'}`}>
                  {stepTitles[n - 1]}
                </span>
                {n < 3 && <div className="h-px w-8 bg-border" />}
              </div>
            ))}
          </div>
        </CardHeader>

        <CardContent>
          {step === 1 && (
            <form onSubmit={e => { e.preventDefault(); setStep(2) }} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={form.email} onChange={e => set('email', e.target.value)} required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <Input id="password" type="password" value={form.password} onChange={e => set('password', e.target.value)} required minLength={8} />
                <p className="text-xs text-muted-foreground">Minimum 8 characters</p>
              </div>
              <Button type="submit" className="w-full">Continue →</Button>
            </form>
          )}

          {step === 2 && (
            <form onSubmit={e => { e.preventDefault(); setStep(3) }} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Name</Label>
                  <Input id="name" value={form.name} onChange={e => set('name', e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="age">Age</Label>
                  <Input id="age" type="number" min={14} max={100} value={form.age} onChange={e => set('age', e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="weight">Weight (kg)</Label>
                  <Input id="weight" type="number" step="0.1" value={form.weight_kg} onChange={e => set('weight_kg', e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="height">Height (cm)</Label>
                  <Input id="height" type="number" value={form.height_cm} onChange={e => set('height_cm', e.target.value)} required />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="sex">Sex</Label>
                <select id="sex" className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm" value={form.sex} onChange={e => set('sex', e.target.value as 'M' | 'F' | 'other')}>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="primary_sport">Primary sport</Label>
                <select id="primary_sport" className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm" value={form.primary_sport} onChange={e => { const s = e.target.value as Sport; set('primary_sport', s); if (!form.sports.includes(s)) set('sports', [...form.sports, s]) }}>
                  {SPORTS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>

              <div className="space-y-2">
                <Label>Sports you train</Label>
                <div className="flex gap-3 flex-wrap">
                  {SPORTS.map(s => (
                    <label key={s.value} className="flex items-center gap-1.5 text-sm">
                      <input type="checkbox" checked={form.sports.includes(s.value)} onChange={() => toggleSport(s.value)} />
                      {s.label}
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="goals">Goals <span className="text-muted-foreground text-xs">(comma-separated)</span></Label>
                <Input id="goals" placeholder="e.g. Run a 5K, Build muscle" value={form.goals} onChange={e => set('goals', e.target.value)} required />
              </div>

              <div className="space-y-2">
                <Label>Available days</Label>
                <div className="flex gap-2">
                  {DAYS.map((d, i) => (
                    <label key={i} className="flex flex-col items-center gap-1 text-xs">
                      <input type="checkbox" checked={form.available_days.includes(i)} onChange={() => toggleDay(i)} />
                      {d}
                    </label>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="hours_per_week">Hours per week</Label>
                <Input id="hours_per_week" type="number" min={1} step="0.5" value={form.hours_per_week} onChange={e => set('hours_per_week', e.target.value)} required />
              </div>

              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setStep(1)}>← Back</Button>
                <Button type="submit" className="flex-1">Continue →</Button>
              </div>
            </form>
          )}

          {step === 3 && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="plan_start_date">Plan start date</Label>
                <Input id="plan_start_date" type="date" value={form.plan_start_date} onChange={e => set('plan_start_date', e.target.value)} required />
                <p className="text-xs text-muted-foreground">Your first week starts on this date.</p>
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setStep(2)}>← Back</Button>
                <Button type="submit" className="flex-1" disabled={loading}>
                  {loading ? 'Generating…' : 'Generate my plan →'}
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
