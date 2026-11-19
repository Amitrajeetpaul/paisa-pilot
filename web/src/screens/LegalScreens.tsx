import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Wordmark } from '../components/Logo'

const REPO = 'https://github.com/Amitrajeetpaul/paisa-pilot'

function Page({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="text-navy mx-auto max-w-2xl px-6 py-10">
      <Link to="/" aria-label="Back to home">
        <Wordmark />
      </Link>
      <h1 className="mt-8 text-3xl font-extrabold">{title}</h1>
      <p className="text-muted mt-1 text-sm">Pilot version. Last updated 20 November 2026.</p>
      <div className="mt-6 flex flex-col gap-5 text-sm leading-relaxed">{children}</div>
      <p className="text-muted mt-10 text-xs">
        <Link to="/privacy" className="underline">Privacy</Link> · <Link to="/terms" className="underline">Terms</Link> ·{' '}
        <Link to="/" className="underline">Home</Link>
      </p>
    </div>
  )
}

function H({ children }: { children: ReactNode }) {
  return <h2 className="mt-2 text-lg font-bold">{children}</h2>
}

export function PrivacyScreen() {
  return (
    <Page title="Privacy">
      <p>
        Paisa Pilot is a pilot. We handle financial documents, so we keep this short, plain and honest. We collect only what
        the app needs to work, and you can delete it yourself at any time.
      </p>
      <H>What we collect, and why</H>
      <ul className="list-disc pl-5">
        <li><b>Documents you upload</b> (payslip, Form 16, bank statement, PF passbook, AIS), only to read the numbers off them.</li>
        <li><b>The values you confirm</b> on the Confirm screen, to work out what you may be owed or losing.</li>
        <li><b>An email address</b>, only if you join the pilot list, and only to contact you about the pilot.</li>
        <li><b>Anonymous usage events</b> (for example "a document was uploaded"), using a random id kept in your browser. They never contain your documents, numbers or name. If your browser sends Do Not Track, we send nothing.</li>
        <li><b>Notes you send</b> through "Report a wrong number".</li>
      </ul>
      <p>We do not use cookies for advertising, we do not sell data, and we do not connect to your bank.</p>
      <H>How long we keep it</H>
      <ul className="list-disc pl-5">
        <li>Uploaded files are deleted automatically within about a day.</li>
        <li>Your confirmed values and results are deleted automatically after 7 days.</li>
        <li>You can delete everything now: open the account menu and choose <b>Delete my data</b>.</li>
        <li>Pilot-list emails are kept until you ask us to remove them or the pilot ends.</li>
      </ul>
      <H>Who sees your documents</H>
      <p>
        Your uploaded documents are sent to Google's Gemini service to read them, and are stored on Google Cloud in India
        (Mumbai region), encrypted at rest. Google's own terms apply to that processing. Nobody on our side browses your
        documents.
      </p>
      <H>What the AI does and does not do</H>
      <p>
        The AI reads your documents and explains results in plain words. Every rupee figure comes from a tested rules
        engine, not from the AI. Nothing is filed, sent or paid for you, and we never ask for passwords or OTPs.
      </p>
      <H>Your choices</H>
      <p>
        You can use the sample profile without uploading anything. To remove your email from the pilot list or ask a
        question about your data, open an issue at{' '}
        <a href={REPO + '/issues'} className="text-teal underline" target="_blank" rel="noreferrer">our project page</a>.
      </p>
      <p className="text-muted">
        This is a pilot notice, not legal advice, and it will be reviewed by counsel before any public launch.
      </p>
    </Page>
  )
}

export function TermsScreen() {
  return (
    <Page title="Terms of use">
      <H>What Paisa Pilot is</H>
      <p>
        Paisa Pilot helps you spot money you may be owed and money you may be losing, and prepares drafts and summaries for
        you to use. It is a pilot and a preparation aid.
      </p>
      <H>It is not advice from a professional</H>
      <ul className="list-disc pl-5">
        <li>It is not a registered tax, investment or insurance adviser. It does not replace a professional for complex situations.</li>
        <li>The tax and PF figures are <b>estimates from this year's published rules</b>, not a filing. A formal review of our tax rules by a chartered accountant is planned before any public launch.</li>
        <li>We name categories (such as an FD or a term plan), never specific funds, stocks or policies, and we never promise a refund or a return.</li>
        <li>Some things are not covered, such as HRA, home-loan interest, capital gains and business income. A CA's help is worth it for those, and for any tax notice.</li>
      </ul>
      <H>You stay in control</H>
      <p>
        We never file a return, send a message, cancel a subscription or move money. Drafts are for you to review and send.
        Check every number on the Confirm screen, because the app reads documents with AI and can misread them.
      </p>
      <H>Use it fairly</H>
      <p>Upload only your own documents, or documents you have permission to use. Do not misuse the service.</p>
      <H>No warranty</H>
      <p>
        The service is provided "as is" during the pilot, without warranty, and may change or stop. To the extent the law
        allows, we are not liable for decisions made from its output. This is a pilot notice, not legal advice, and it will be
        reviewed by counsel before any public launch.
      </p>
    </Page>
  )
}
