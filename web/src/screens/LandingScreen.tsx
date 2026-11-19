import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, api } from '../lib/api'
import { track } from '../lib/track'
import { Button } from '../components/Button'
import { Icon, type IconName } from '../components/Icon'
import { Wordmark } from '../components/Logo'

const PROBLEMS = [
  {
    icon: 'wallet' as IconName,
    title: 'Money you are owed but never claim',
    body: 'Old PF accounts from past jobs, extra tax cut (TDS), the wrong tax option, failed or double-paid refunds.',
  },
  {
    icon: 'droplet' as IconName,
    title: 'Money that leaks every month',
    body: 'Forgotten subscriptions, old UPI AutoPay still running, hidden fees and costly phone plans, loans with high interest.',
  },
  {
    icon: 'compass' as IconName,
    title: 'Money choices nobody taught',
    body: 'Old or new tax option, how much to save, where to put extra money (SIP, FD or PPF), what type of insurance, payslip and Form 16 jargon.',
  },
]

const PROOF_POINTS = [
  { figure: '₹9,330 crore', detail: 'sitting in 30.9 lakh dormant PF accounts', source: 'EPFO, 2026' },
  { figure: '24.64 lakh', detail: 'tax returns pending over 90 days', source: 'Parliament, 2026' },
  { figure: '~1,000', detail: 'SEBI advisers for 20 crore+ demat accounts', source: '2026' },
]

const STAGES = [
  { n: 1, title: 'Upload', body: 'Payslip, Form 16, bank statement, AIS — consent first.' },
  { n: 2, title: 'Read', body: 'We read your photos and PDFs and pull out the numbers, flagging anything we are unsure about.' },
  { n: 3, title: 'Confirm', body: 'You fix anything wrong. Nothing runs on unchecked data.' },
  { n: 4, title: 'Calculate', body: 'Tested tax and savings rules do the maths, not an AI guess. Same input, same answer.' },
  { n: 5, title: 'Explain', body: 'Money Finder, Leak Fixer and your tax check-up explain what they found in plain words.' },
  { n: 6, title: 'Output', body: 'Source trail, filled PF forms, cancel and refund drafts — you send them.' },
]

const COMPETITION = [
  ['They show, we act', 'Show where your money went', 'Find money you are owed and stop leaks'],
  ['Who pays them', 'Trading, loans, commissions', 'We earn only after a real, verified saving'],
  ['Subscriptions', 'Manage UPI AutoPay in each UPI app', 'UPI and card plans in one list, cancel drafts'],
  ['Tax', 'File your return, pre-fill Form 16 and AIS', 'Also look for old PF and missed refunds'],
  ['Trust', 'Show a score, not how it was worked out', 'Every number shows its source, rules tested'],
  ['Next step', 'Show a chart, you work out what to do', 'Drafts the form or message, you just send it'],
]

function WaitlistForm() {
  const [email, setEmail] = useState('')
  const [agree, setAgree] = useState(false)
  const [state, setState] = useState<'idle' | 'sending' | 'done'>('idle')
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setState('sending')
    setError(null)
    try {
      await api.joinWaitlist(email, agree)
      track('waitlist_joined')
      setState('done')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
      setState('idle')
    }
  }

  if (state === 'done') return <p className="text-teal mt-6 font-semibold">Thanks, you are on the pilot list. We will be in touch.</p>
  return (
    <form onSubmit={submit} className="mx-auto mt-8 max-w-md text-left">
      <p className="text-center text-sm font-semibold text-white/90">Want to try it with your own documents? Join the pilot list.</p>
      <div className="mt-3 flex flex-col gap-3 sm:flex-row">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@email.com"
          aria-label="Email address"
          className="text-navy min-h-11 flex-1 rounded-[18px] border-0 bg-white px-4 outline-none"
        />
        <Button type="submit" variant="primary" loading={state === 'sending'} disabled={!agree}>
          Join the list
        </Button>
      </div>
      <label className="mt-3 flex items-start gap-2 text-xs text-white/80">
        <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} className="mt-0.5 h-4 w-4 accent-[#2EC4B6]" />
        <span>
          I agree to be contacted about the pilot. See the <Link to="/privacy" className="underline">Privacy notice</Link>.
        </span>
      </label>
      {error && <p className="mt-2 text-sm font-medium text-[#FFB4AB]" role="alert">{error}</p>}
    </form>
  )
}

export function LandingScreen() {
  useEffect(() => {
    track('landing_view')
  }, [])

  return (
    <div className="text-navy">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <Wordmark />
        <nav className="hidden items-center gap-6 text-sm font-semibold md:flex">
          <a href="#problems" className="hover:text-coral">
            Problems
          </a>
          <a href="#how" className="hover:text-coral">
            How it works
          </a>
          <a href="#trust" className="hover:text-coral">
            Trust
          </a>
        </nav>
        <Link to="/app/consent">
          <Button variant="primary">Try it</Button>
        </Link>
      </header>

      <section className="mx-auto max-w-4xl px-6 py-16 text-center">
        <h1 className="text-4xl font-extrabold leading-tight tracking-tight md:text-6xl">
          Finds your money. Fixes your leaks. <span className="text-coral">Advises you with proof.</span>
        </h1>
        <p className="text-muted mx-auto mt-6 max-w-2xl text-lg">
          Many Indians, working or retired, young, middle-aged and old, manage money without anyone checking whether
          they are making the most of it.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-4">
          <Link to="/app/consent">
            <Button variant="primary">Try with sample data</Button>
          </Link>
          <a href="#problems">
            <Button variant="outline">See the problem</Button>
          </a>
        </div>
        <p className="text-muted mt-4 flex items-center justify-center gap-2 text-sm">
          <Icon name="lock" size={14} /> No sign-up. Nothing is filed or sent without you. Delete your data anytime.
        </p>

        <div className="mx-auto mt-12 max-w-md text-left" aria-label="Product preview">
          <div className="bg-hero-card rounded-[28px] p-6 text-white shadow-2xl">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-white/80">Money found for you</span>
              <span className="bg-yellow text-navy rounded-full px-2.5 py-0.5 text-xs font-bold">SAMPLE</span>
            </div>
            <div className="mt-2 text-5xl font-extrabold tracking-tight">₹2,13,700</div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-white/10 p-3">
                <div className="text-lg font-bold">₹75,400</div>
                <div className="text-xs text-white/70">every year</div>
              </div>
              <div className="rounded-2xl bg-white/10 p-3">
                <div className="text-lg font-bold">₹1,38,300</div>
                <div className="text-xs text-white/70">one-time, if confirmed</div>
              </div>
            </div>
          </div>
          <div className="border-line -mt-3 mx-4 rounded-[20px] border bg-white p-4 shadow-lg">
            <div className="flex items-center gap-3">
              <span className="bg-icon-tile text-coral-dark flex h-10 w-10 items-center justify-center rounded-xl">
                <Icon name="book" size={20} />
              </span>
              <div className="flex-1">
                <p className="text-navy text-sm font-bold">Old PF account found</p>
                <p className="text-muted text-xs">2 accounts from past employers, not transferred</p>
              </div>
              <span className="text-navy text-lg font-extrabold">₹1,11,300</span>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 py-10">
        <div className="grid gap-4 md:grid-cols-3">
          {PROOF_POINTS.map((p) => (
            <div key={p.figure} className="border-line rounded-[20px] border bg-white p-6 text-center">
              <div className="text-coral text-3xl font-extrabold">{p.figure}</div>
              <p className="text-navy mt-2 text-sm font-medium">{p.detail}</p>
              <p className="text-muted mt-1 text-xs">Source: {p.source}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="problems" className="mx-auto max-w-5xl px-6 py-16">
        <h2 className="text-center text-3xl font-extrabold">Three ways money is lost</h2>
        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {PROBLEMS.map((p) => (
            <div key={p.title} className="border-line rounded-[20px] border bg-white p-6">
              <div className="bg-icon-tile text-coral-dark flex h-12 w-12 items-center justify-center rounded-2xl">
                <Icon name={p.icon} size={24} />
              </div>
              <h3 className="mt-4 text-lg font-bold">{p.title}</h3>
              <p className="text-muted mt-2 text-sm leading-relaxed">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-navy px-6 py-16 text-white">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-3xl font-extrabold">Find · Fix · Advise</h2>
          <div className="mt-8 grid gap-6 md:grid-cols-3">
            {[
              ['Find', 'Old PF accounts, missed refunds, the right tax option — on your numbers.'],
              ['Fix', 'Idle subscriptions, live AutoPay, costly plans, high-interest loans.'],
              ['Advise', 'Salary and Form 16 explained, savings targets, goal categories, grounded in your data.'],
            ].map(([title, body]) => (
              <div key={title} className="rounded-[20px] bg-white/10 p-6">
                <h3 className="text-coral text-xl font-bold">{title}</h3>
                <p className="mt-2 text-sm text-white/80">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="how" className="mx-auto max-w-5xl px-6 py-16">
        <h2 className="text-center text-3xl font-extrabold">How it works</h2>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {STAGES.map((s) => (
            <div key={s.n} className="border-line rounded-[20px] border bg-white p-5">
              <div className="bg-coral-tint text-coral flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold">
                {s.n}
              </div>
              <h3 className="mt-3 font-bold">{s.title}</h3>
              <p className="text-muted mt-1 text-sm">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="trust" className="mx-auto max-w-5xl px-6 py-16">
        <h2 className="text-center text-3xl font-extrabold">Trust by design</h2>
        <ul className="text-muted mx-auto mt-6 max-w-2xl list-disc space-y-2 pl-6 text-sm">
          <li>AI reads and explains. Tested rules do the maths — same input, same answer, every time.</li>
          <li>Tap any number to see how we got it: what we used, the rule, and the official source.</li>
          <li>Nothing runs until you confirm it.</li>
          <li>We never file, move money, or touch your bank without you.</li>
          <li>Consent first, encrypted, uploads auto-deleted within 24 hours. Delete everything yourself anytime.</li>
        </ul>
        <p className="text-navy mx-auto mt-6 max-w-2xl rounded-2xl bg-[var(--color-warn-tint)] p-4 text-center text-sm font-medium">
          {"We don't claim results yet — impact will be measured in a real pilot."}
        </p>
      </section>

      <section className="mx-auto max-w-4xl px-6 py-16">
        <h2 className="text-center text-3xl font-extrabold">How we're different</h2>
        <div className="border-line mt-8 overflow-x-auto rounded-[20px] border">
          <table className="w-full text-left text-sm">
            <thead className="bg-cream">
              <tr>
                <th className="p-3 font-bold">Today</th>
                <th className="p-3 font-bold">Other apps</th>
                <th className="p-3 font-bold">Paisa Pilot</th>
              </tr>
            </thead>
            <tbody>
              {COMPETITION.map((row) => (
                <tr key={row[0]} className="border-line border-t">
                  {row.map((cell, i) => (
                    <td key={i} className={`p-3 ${i === 2 ? 'text-teal font-semibold' : 'text-muted'}`}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bg-navy px-6 py-16 text-center text-white">
        <h2 className="text-3xl font-extrabold">See what you are missing</h2>
        <p className="mt-2 text-white/80">Try it on a sample profile in one click, or add your own documents.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link to="/app/consent">
            <Button variant="primary">Try with sample data</Button>
          </Link>
          <Link to="/app/consent">
            <Button variant="outline">Use my own documents</Button>
          </Link>
        </div>
        <WaitlistForm />
      </section>

      <footer className="text-muted px-6 py-8 text-center text-xs">
        © 2026 Paisa Pilot · git_happens · Sample data shown throughout this demo. ·{' '}
        <Link to="/privacy" className="underline">Privacy</Link> · <Link to="/terms" className="underline">Terms</Link>
      </footer>
    </div>
  )
}
