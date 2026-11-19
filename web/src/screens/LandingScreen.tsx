import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/Button'
import { Wordmark } from '../components/Logo'

const PROBLEMS = [
  {
    icon: '💰',
    title: 'Money you are owed but never claim',
    body: 'Old PF accounts from past jobs, extra tax cut (TDS), the wrong tax option, failed or double-paid refunds.',
  },
  {
    icon: '🩹',
    title: 'Money that leaks every month',
    body: 'Forgotten subscriptions, old UPI AutoPay still running, hidden fees and costly phone plans, loans with high interest.',
  },
  {
    icon: '🧭',
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

export function LandingScreen() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)

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
        <div className="mt-8 flex justify-center gap-4">
          <Link to="/app/consent">
            <Button variant="primary">Try with sample data</Button>
          </Link>
          <a href="#problems">
            <Button variant="outline">See the problem</Button>
          </a>
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
              <div className="bg-icon-tile flex h-12 w-12 items-center justify-center rounded-2xl text-2xl">{p.icon}</div>
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
          <li>Tap any number to see its source: inputs used, rule, config version, official link.</li>
          <li>Nothing runs until you confirm it.</li>
          <li>We never file, move money, or touch your bank without you.</li>
          <li>Consent first, encrypted, uploads auto-deleted within 24 hours.</li>
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
        <h2 className="text-3xl font-extrabold">Join the pilot</h2>
        <p className="mt-2 text-white/80">Be one of the first to try Paisa Pilot with your own numbers.</p>
        {submitted ? (
          <p className="text-teal mt-6 font-semibold">Thanks — we'll be in touch.</p>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault()
              setSubmitted(true)
            }}
            className="mx-auto mt-6 flex max-w-md flex-col gap-3 sm:flex-row"
          >
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@email.com"
              aria-label="Email address"
              className="min-h-11 flex-1 rounded-[18px] border-0 px-4 text-navy outline-none"
            />
            <Button type="submit" variant="primary">
              Join the pilot
            </Button>
          </form>
        )}
      </section>

      <footer className="text-muted px-6 py-8 text-center text-xs">
        © 2026 Paisa Pilot · git_happens · Sample data shown throughout this demo.
      </footer>
    </div>
  )
}
