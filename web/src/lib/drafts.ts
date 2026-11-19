import type { MoneyFinderCard } from './api'
import { formatINR } from './format'

/** Draft message templates. The user edits and sends these themselves --
 * per brief principle 4, the app never files or sends anything on its own. */
export function buildDraftText(card: Pick<MoneyFinderCard, 'card_id' | 'title' | 'detail' | 'amount'>): {
  heading: string
  body: string
} {
  const id = card.card_id

  if (id === 'old_pf_accounts') {
    return {
      heading: 'PF transfer claim (Form 13)',
      body:
        `To: EPFO / my current employer's HR\n\nSubject: Request to transfer PF from previous employer(s)\n\n` +
        `I would like to transfer my EPF balance from my previous employer account(s) to my current active account.\n\n` +
        `Details found: ${card.detail}. Combined balance: ${formatINR(card.amount)} (${card.title}).\n\n` +
        `I will submit Form 13 (online, via the UAN member portal) with my UAN and previous employer details attached. ` +
        `Please confirm the steps on your end.\n\n[Your name]\n[Your UAN]`,
    }
  }

  if (id === 'extra_tds_refund' || id === 'refund_hunter') {
    return {
      heading: 'Refund / claim request',
      body:
        `To: ${id === 'refund_hunter' ? 'Bank customer care' : 'Income Tax Department (via ITR filing / AIS feedback)'}\n\n` +
        `Subject: Request to review a possible ${id === 'refund_hunter' ? 'failed/duplicate transaction' : 'excess TDS deduction'}\n\n` +
        `${card.detail}. Amount in question: ${formatINR(card.amount)}.\n\n` +
        `Could you please review this and confirm the next step to recover it? I can share supporting statements if needed.\n\n[Your name]`,
    }
  }

  if (id.startsWith('subscription_')) {
    return {
      heading: 'Cancel subscription',
      body:
        `To: ${card.title}\n\nSubject: Please cancel my subscription\n\n` +
        `I'd like to cancel my subscription (${formatINR(card.amount)}/month) effective immediately. ` +
        `Please confirm the cancellation and stop any further charges.\n\n[Your name / account email]`,
    }
  }

  if (id.startsWith('autopay_')) {
    return {
      heading: 'Review AutoPay',
      body:
        `To: ${card.title}\n\nSubject: Reviewing my UPI AutoPay mandate\n\n` +
        `I'm reviewing my recurring payment of ${formatINR(card.amount)}/month to you. Could you confirm what this covers, ` +
        `and let me know if there's a lower-cost plan available?\n\n[Your name]`,
    }
  }

  return {
    heading: card.title,
    body: `${card.detail}\n\nAmount: ${formatINR(card.amount)}`,
  }
}
