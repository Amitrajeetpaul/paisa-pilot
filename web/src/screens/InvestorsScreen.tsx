import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Wordmark } from '../components/Logo'
import { ThemeToggle } from '../components/ThemeToggle'

function Stat({ value, label, source }: { value: string; label: string; source: string }) {
  return (
    <div className="card p-4">
      <p className="tabular text-ink text-2xl font-extrabold">{value}</p>
      <p className="text-ink mt-1 text-sm font-semibold">{label}</p>
      <p className="text-muted mt-1 text-xs">{source}</p>
    </div>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-10">
      <h2 className="text-ink text-xl font-extrabold tracking-tight">{title}</h2>
      <div className="text-muted mt-3 space-y-3 text-sm leading-relaxed">{children}</div>
    </section>
  )
}

/** For investors and partners: the case, stated honestly, with sources. No invented traction. */
export function InvestorsScreen() {
  return (
    <div className="text-ink mx-auto max-w-4xl px-5 pb-16" style={{ paddingTop: 'max(env(safe-area-inset-top), 1.5rem)' }}>
      <header className="flex items-center justify-between py-4">
        <Link to="/" aria-label="Paisa Pilot home">
          <Wordmark />
        </Link>
        <ThemeToggle />
      </header>

      <p className="text-coral-dark mt-6 text-sm font-bold uppercase tracking-wide">For investors and partners</p>
      <h1 className="mt-2 text-3xl font-extrabold leading-tight tracking-tight sm:text-4xl">
        A tax and money co-pilot that gets the numbers right, and shows its working.
      </h1>
      <p className="text-muted mt-3 max-w-2xl text-base">
        Every rupee figure comes from a tested rules engine, and the AI only reads documents and explains. Each answer cites the section of law it relies on. Built on Google Cloud and Gemini.
      </p>

      <Section title="The problem">
        <p>
          Filing itself is cheap now, but getting it right is not. People miss refunds, pick the wrong tax regime, overpay through
          forgotten subscriptions, and small businesses lose GST input credit they were owed. General chatbots get tax maths and
          recent rule changes wrong, and a new Income-tax Act took effect on 1 April 2026.
        </p>
      </Section>

      <Section title="The market">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Stat value="7.8 crore+" label="Income-tax returns for AY 2026-27" source="Income Tax Department, by 31 Aug 2026 (press reports)" />
          <Stat value="1.67 crore" label="Active GST taxpayers" source="GSTN, 30 Jun 2026" />
          <Stat value="₹11–24" label="Price of DIY filing in Paytm, PhonePe, JioFinance" source="Business Today, Jul 2026" />
        </div>
        <p>
          Filing is now a commodity, and the leading filer reported about ₹272 crore revenue with a ₹96 crore loss in FY25 (Entrackr /
          Inc42). We do not compete on filing price. We compete on accuracy, year-round help and trust.
        </p>
      </Section>

      <Section title="Who we start with">
        <p>
          <b className="text-ink">Freelancers and very small GST businesses</b>: people who need help all year, not once a year, and
          who are under-served by salaried-only tools. Salaried users come next through employers.
        </p>
      </Section>

      <Section title="What is built and working">
        <ul className="list-disc space-y-1 pl-5">
          <li>Reads payslips, Form 16, bank statements, PF passbooks and AIS with Gemini; every value is confirmed by the user.</li>
          <li>Tax engine with both regimes, rebate and surcharge marginal relief, senior-citizen slabs; checked against an independent reference across hundreds of incomes.</li>
          <li>Tax-saving suggestions from the person's own documents, a filing pack with a checklist, and deadline reminders.</li>
          <li>GST: questions answered with citations, GSTR-3B draft, and GSTR-2B reconciliation that flags input credit at risk.</li>
          <li>Leak finder, subscription-usage check, spending profile and goal planner.</li>
          <li>Optional accounts with consent and one-tap deletion. Web and Android. Over 300 automated tests; deployed on Cloud Run.</li>
        </ul>
      </Section>

      <Section title="How it makes money (planned)">
        <ul className="list-disc space-y-1 pl-5">
          <li><b className="text-ink">Free</b>: reading documents, finding money, tax tips, reminders.</li>
          <li><b className="text-ink">Paid help</b>: a reviewed filing pack and expert-assisted filing through partner CAs (the market charges about ₹999–2,500).</li>
          <li><b className="text-ink">GST subscription</b> for small businesses: monthly reconciliation and reminders.</li>
          <li><b className="text-ink">Partners</b>: employers (a payroll benefit), CA firms (a client tool) and banks.</li>
        </ul>
        <p>Pricing is a hypothesis to test in the pilot, not a result.</p>
      </Section>

      <Section title="Why us">
        <ul className="list-disc space-y-1 pl-5">
          <li>Numbers you can audit: a rules engine, not a chatbot, with the law section behind each answer.</li>
          <li>Rules versioned by year as the new Act arrives; checks that block any AI-stated number not produced by the engine.</li>
          <li>Privacy by design: only confirmed values are kept, with consent, and erasable at any time.</li>
        </ul>
      </Section>

      <Section title="Honest status and risks">
        <ul className="list-disc space-y-1 pl-5">
          <li><b className="text-ink">No users yet.</b> We have not run the pilot, so we claim no traction.</li>
          <li>Our law notes are not yet reviewed by a chartered accountant. A CA reviewer is our first hire or advisor.</li>
          <li>Regulation: we give category-level guidance only (no named funds or policies) and never file or move money for anyone. Bank data via Account Aggregator needs a regulated partner.</li>
          <li>Google Play rules limit SMS reading, so spending comes from statements the user uploads.</li>
        </ul>
      </Section>

      <Section title="The next 90 days">
        <ol className="list-decimal space-y-1 pl-5">
          <li>Sign a practising CA as advisor; review every rule and note.</li>
          <li>Run a pilot with 30–50 freelancers and small GST businesses; measure activation, accuracy and willingness to pay.</li>
          <li>Sign one distribution partner (a CA firm or an employer).</li>
          <li>Ship on the Play Store (closed test, then production) and add usage limits and monitoring.</li>
        </ol>
      </Section>

      <div className="mt-12 flex flex-wrap gap-3">
        <Link to="/app/consent" className="bg-coral-button press inline-flex min-h-11 items-center rounded-xl px-5 text-sm font-bold">
          Try the live demo
        </Link>
        <Link to="/" className="border-line text-ink inline-flex min-h-11 items-center rounded-xl border px-5 text-sm font-semibold">
          Back to home
        </Link>
      </div>
      <p className="text-muted mt-6 text-xs">
        Market figures are from public reports with the dates shown; full sources are in our research notes. This page is not an offer of securities.
      </p>
    </div>
  )
}
