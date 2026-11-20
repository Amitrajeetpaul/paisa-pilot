#!/usr/bin/env python3
"""
Generates the comprehensive Paisa Pilot Pitch Deck & Technical Architecture PDF.
Optimized for exactly 4 clean, high-impact pages.
"""

import os
import subprocess
import sys

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Paisa Pilot - Pitch Deck & Technical Architecture</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

  @page {
    size: A4 portrait;
    margin: 10mm 12mm 10mm 12mm;
  }

  * {
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #14152E;
    background: #FFFFFF;
    line-height: 1.35;
    font-size: 8.8pt;
    margin: 0;
    padding: 0;
  }

  .page {
    page-break-after: always;
    height: 275mm;
    max-height: 275mm;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .page:last-child {
    page-break-after: avoid;
  }

  /* Header & Footer */
  .doc-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #E6E8EE;
    padding-bottom: 5px;
    margin-bottom: 10px;
  }

  .doc-header .logo {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 800;
    font-size: 11pt;
    color: #14152E;
  }

  .doc-header .logo .badge {
    background: #E23D43;
    color: #FFFFFF;
    font-size: 7pt;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .doc-header .tagline {
    font-size: 7.5pt;
    color: #5F6577;
    font-weight: 500;
  }

  .doc-footer {
    border-top: 1px solid #E6E8EE;
    padding-top: 5px;
    display: flex;
    justify-content: space-between;
    font-size: 7.5pt;
    color: #5F6577;
  }

  /* Typography */
  h1 {
    font-size: 17pt;
    font-weight: 800;
    color: #14152E;
    letter-spacing: -0.4px;
    margin: 0 0 4px 0;
    line-height: 1.15;
  }

  h2 {
    font-size: 11.5pt;
    font-weight: 800;
    color: #14152E;
    letter-spacing: -0.2px;
    margin: 10px 0 6px 0;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  h2::before {
    content: '';
    display: inline-block;
    width: 4px;
    height: 14px;
    background: #E23D43;
    border-radius: 2px;
  }

  h3 {
    font-size: 9.5pt;
    font-weight: 700;
    color: #14152E;
    margin: 4px 0 2px 0;
  }

  p {
    margin: 0 0 5px 0;
    color: #30305A;
  }

  .lead {
    font-size: 9.8pt;
    font-weight: 500;
    color: #5F6577;
    margin-bottom: 8px;
    line-height: 1.35;
  }

  .coral-text { color: #E23D43; }
  .teal-text { color: #12A594; }
  .amber-text { color: #F5A524; }

  /* Cards & Grids */
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 8px;
  }

  .grid-3 {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
    margin-bottom: 8px;
  }

  .grid-4 {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 6px;
    margin-bottom: 8px;
  }

  .card {
    background: #F8F9FA;
    border: 1px solid #E6E8EE;
    border-radius: 8px;
    padding: 8px 10px;
  }

  .card-highlight {
    background: #FFF5F5;
    border: 1px solid #FDCED0;
  }

  .card-navy {
    background: linear-gradient(145deg, #1D1E44, #14152E);
    color: #FFFFFF;
    border: none;
  }

  .card-navy h3, .card-navy p, .card-navy span {
    color: #FFFFFF;
  }

  .stat-card {
    text-align: center;
    padding: 8px 4px;
    background: #FFFFFF;
    border: 1px solid #E6E8EE;
    border-radius: 8px;
    box-shadow: 0 1px 2px rgba(20, 21, 46, 0.03);
  }

  .stat-number {
    font-size: 15pt;
    font-weight: 800;
    color: #E23D43;
    line-height: 1.1;
  }

  .stat-label {
    font-size: 7pt;
    font-weight: 700;
    color: #5F6577;
    margin-top: 2px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }

  .stat-sub {
    font-size: 6.8pt;
    color: #8C92A4;
    margin-top: 1px;
  }

  /* Table styling */
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 7.8pt;
    margin: 4px 0 8px 0;
  }

  th {
    background: #14152E;
    color: #FFFFFF;
    font-weight: 700;
    text-align: left;
    padding: 5px 8px;
    font-size: 7.5pt;
    letter-spacing: 0.2px;
  }

  th:first-child { border-top-left-radius: 5px; }
  th:last-child { border-top-right-radius: 5px; }

  td {
    padding: 4px 8px;
    border-bottom: 1px solid #E6E8EE;
    vertical-align: top;
  }

  tr:nth-child(even) td {
    background: #F9FAFB;
  }

  .code-cell {
    font-family: 'JetBrains Mono', monospace;
    font-size: 7.2pt;
    color: #B42318;
    background: #FEE4E2;
    padding: 1px 4px;
    border-radius: 3px;
    display: inline-block;
  }

  .badge-tag {
    display: inline-block;
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 6.8pt;
    font-weight: 700;
    text-transform: uppercase;
  }

  .badge-gemini { background: #E0EAFF; color: #1D4ED8; }
  .badge-adk { background: #FEF3C7; color: #B45309; }
  .badge-engine { background: #D1FAE5; color: #047857; }
  .badge-cloud { background: #EDE9FE; color: #6D28D9; }

  /* Architecture Box */
  .arch-box {
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 7px 9px;
    background: #FFFFFF;
  }

  .arch-box-title {
    font-weight: 700;
    font-size: 8.5pt;
    color: #14152E;
    display: flex;
    justify-content: space-between;
    border-bottom: 1px dashed #E2E8F0;
    padding-bottom: 3px;
    margin-bottom: 4px;
  }

  .key-bullet {
    position: relative;
    padding-left: 12px;
    margin-bottom: 3px;
    font-size: 8.2pt;
    line-height: 1.3;
  }

  .key-bullet::before {
    content: '▪';
    position: absolute;
    left: 0;
    color: #E23D43;
    font-size: 9pt;
    line-height: 1;
  }

  .callout {
    background: #F0FDF4;
    border-left: 3px solid #12A594;
    padding: 6px 10px;
    border-radius: 0 6px 6px 0;
    margin: 6px 0;
    font-size: 8.2pt;
  }

  .callout strong { color: #065F46; }
</style>
</head>
<body>

<!-- ================= PAGE 1 ================= -->
<div class="page">
  <div>
    <div class="doc-header">
      <div class="logo">
        <span>PAISA PILOT</span>
        <span class="badge">Google Startup Buildathon 2026</span>
      </div>
      <div class="tagline">git_happens · Confidential Pitch Deck & Architecture</div>
    </div>

    <h1>Paisa Pilot: The AI Money Co-Pilot with Proof</h1>
    <p class="lead">Finds your money, fixes your leaks, and advises you with mathematical proof. Built with an anti-hallucination deterministic core on Google Cloud & Gemini.</p>

    <div class="grid-4">
      <div class="stat-card">
        <div class="stat-number">₹9,330 Cr</div>
        <div class="stat-label">Dormant PF</div>
        <div class="stat-sub">30.9L Accounts (EPFO 2026)</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">24.64 L</div>
        <div class="stat-label">Pending ITRs</div>
        <div class="stat-sub">&gt;90 Days (Parliament 2026)</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">~1,000</div>
        <div class="stat-label">SEBI Advisers</div>
        <div class="stat-sub">For 20Cr+ Accounts</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">₹30K-75K</div>
        <div class="stat-label">Tax Trap / User</div>
        <div class="stat-sub">Lost in Wrong Regime</div>
      </div>
    </div>

    <h2>1. Problem Statement: The Silent Indian Wealth Leak</h2>
    <div class="grid-2">
      <div class="card">
        <h3>1. The Abandoned Wealth Trap</h3>
        <p style="font-size: 8.2pt;">When young professionals switch jobs, their Employee Provident Fund (PF) accounts get abandoned due to UAN fragmentation and paperwork. Over ₹9,330 Crores in retirement savings sits idle earning zero compound interest.</p>
        <h3>2. The Tax Choice Paralysis</h3>
        <p style="font-size: 8.2pt;">India's dual-regime tax system (Old vs New Regime under FY 2025-26 Budget rules) forces salaried employees to choose blindly. 70% remain defaulted into suboptimal options, overpaying ₹30,000 to ₹75,000 yearly.</p>
      </div>
      <div class="card">
        <h3>3. Micro-Drain: UPI AutoPay & Hidden Leaks</h3>
        <p style="font-size: 8.2pt;">With the explosion of UPI AutoPay, recurring SaaS subscriptions, gym memberships, and high-interest loan EMIs silently siphon ₹500 to ₹3,000/month from salaried bank accounts without clear visibility.</p>
        <h3>4. The Severe Advisory Deficit</h3>
        <p style="font-size: 8.2pt;">With fewer than 1,000 registered SEBI advisers for 20+ crore retail accounts, 99.9% of Indians lack trustworthy, conflict-free financial advice. Unregulated influencers fill the void with speculative tips.</p>
      </div>
    </div>

    <h2>2. The Startup Pitch: What Paisa Pilot Does</h2>
    <div class="card card-navy" style="margin-bottom: 8px;">
      <h3 style="font-size: 10.5pt; margin-top: 0;">Our Value Proposition</h3>
      <p style="font-size: 8.6pt; line-height: 1.4; margin: 0;">Upload a smartphone photo or PDF of your payslip, Form 16, or bank statement. In 60 seconds, Paisa Pilot extracts the numbers, identifies what you are owed, catches every leak, and generates ready-to-send dispute, cancellation, and transfer drafts — with zero human intervention.</p>
    </div>

    <div class="grid-3">
      <div class="card">
        <h3 class="coral-text">FIND: Unclaimed Money</h3>
        <div class="key-bullet">Old vs New Tax Regime optimization</div>
        <div class="key-bullet">Extra TDS mismatch via 26AS / AIS</div>
        <div class="key-bullet">Dormant PF accounts & lost balances</div>
        <div class="key-bullet">Failed / double-debited UPI refunds</div>
      </div>
      <div class="card">
        <h3 class="amber-text">FIX: Stop Silent Leaks</h3>
        <div class="key-bullet">Idle subscriptions audit</div>
        <div class="key-bullet">Live UPI AutoPay mandate tracker</div>
        <div class="key-bullet">High-interest loan switching & EMI math</div>
        <div class="key-bullet">Pre-filled 1-click cancellation letters</div>
      </div>
      <div class="card">
        <h3 class="teal-text">ADVISE: Actionable Truth</h3>
        <div class="key-bullet">Bilingual Q&A (English & Hindi)</div>
        <div class="key-bullet">Plain-language Form 16 & salary breakdown</div>
        <div class="key-bullet">Target SIP, FD & emergency fund plans</div>
        <div class="key-bullet">SEBI-compliant strict safety guardrail</div>
      </div>
    </div>
  </div>

  <div class="doc-footer">
    <span>Paisa Pilot · Confidential · Google Startup Buildathon India 2026</span>
    <span>Page 1 of 4</span>
  </div>
</div>

<!-- ================= PAGE 2 ================= -->
<div class="page">
  <div>
    <div class="doc-header">
      <div class="logo">
        <span>PAISA PILOT</span>
        <span class="badge">Architecture & Innovation</span>
      </div>
      <div class="tagline">The Anti-Hallucination Deterministic Core</div>
    </div>

    <h2>3. The Golden Rule: Deterministic Anti-Hallucination Architecture</h2>
    <div class="callout">
      <strong>The Absolute Rule:</strong> <em>"The AI never computes a rupee figure. The deterministic rules engine does."</em> Every LLM call in Paisa Pilot explains, extracts, or structures text — it NEVER calculates taxes, interest rates, or refunds.
    </div>

    <p style="font-size: 8.4pt;">Generic LLMs (ChatGPT, Claude) hallucinate tax slabs, misapply Section 87A rebates, and invent compound interest. Under Indian tax law, a miscalculated deduction triggers a 200% penalty. Paisa Pilot enforces absolute safety:</p>

    <div class="grid-2">
      <div class="card card-highlight">
        <h3 class="coral-text">What Gemini & LLMs Do</h3>
        <div class="key-bullet"><strong>Blur-Proof Vision OCR:</strong> Reads crumpled phone photos, low-res scans, and angled payslips.</div>
        <div class="key-bullet"><strong>Deductive Extraction:</strong> Reconstructs missing fields using arithmetic reconciliation prompts.</div>
        <div class="key-bullet"><strong>Natural Explanations:</strong> Translates technical income tax sections into conversational English and Hindi.</div>
        <div class="key-bullet"><strong>Draft Generation:</strong> Formulates ready-to-send dispute emails, Form 13 PF letters, and cancellation texts.</div>
      </div>
      <div class="card" style="background: #F0FDF4; border: 1px solid #BBF7D0;">
        <h3 class="teal-text">What the Rules Engine Does (Zero AI)</h3>
        <div class="key-bullet"><strong>Pure Python Maths:</strong> Standalone package with zero external network or AI imports.</div>
        <div class="key-bullet"><strong>100% Deterministic:</strong> Same input always yields the exact same rupee figure.</div>
        <div class="key-bullet"><strong>Worked-Example Tests:</strong> Every tax bracket, surcharge, cess, and EMI verified against official circulars.</div>
        <div class="key-bullet"><strong>1-Tap Provenance:</strong> Tapping any rupee figure exposes inputs, mathematical formula, and Govt link.</div>
      </div>
    </div>

    <h2>4. Production Tech Stack & Cloud Infrastructure</h2>
    <table>
      <thead>
        <tr>
          <th>Layer</th>
          <th>Technologies Used</th>
          <th>Role & Production Architecture</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Mobile App (APK)</strong></td>
          <td>Capacitor 8.6, Android SDK 36, Java 21</td>
          <td>Native standalone Android APK (<span class="code-cell">paisa-pilot.apk</span>). True edge-to-edge full screen, locked 100% text zoom against system scaling, offline asset bundling.</td>
        </tr>
        <tr>
          <td><strong>Frontend Web</strong></td>
          <td>React 19, TypeScript, Vite 8, Tailwind CSS v4</td>
          <td>ORIGYN design system, responsive mobile & desktop UI, bilingual localization (EN/HI), accessibility conformance. Hosted on Cloud Run.</td>
        </tr>
        <tr>
          <td><strong>Backend API</strong></td>
          <td>FastAPI, Python 3.12, Uvicorn, Pydantic v2</td>
          <td>REST API microservice with CORS support for native mobile apps (<span class="code-cell">capacitor://localhost</span>). Structured routes for documents, calculations, agents, and sessions.</td>
        </tr>
        <tr>
          <td><strong>Cloud Run (Compute)</strong></td>
          <td>Google Cloud Run (<span class="code-cell">asia-south1</span>)</td>
          <td>Serverless container execution, scale-to-zero (<span class="code-cell">min-instances=0</span>), zero idle infrastructure cost, automated CI/CD pipeline via GitHub Actions.</td>
        </tr>
        <tr>
          <td><strong>Storage & Database</strong></td>
          <td>Google Cloud Storage, Google Cloud Firestore</td>
          <td>Encrypted uploads bucket with automated 24-hour cryptographic lifecycle deletion. Firestore NoSQL database for session state and confirmed document data.</td>
        </tr>
        <tr>
          <td><strong>Quality & CI/CD</strong></td>
          <td>GitHub Actions, Pytest, Mypy, Oxlint</td>
          <td>165 automated test suites: unit tests, number provenance tests, contract fixtures, type checking, and production build verifications.</td>
        </tr>
      </tbody>
    </table>

    <h2>5. How We Are Using Google AI Tools & Models</h2>
    <div class="grid-2">
      <div class="arch-box">
        <div class="arch-box-title">
          <span>Gemini 2.5 Flash Lite & Flash</span>
          <span class="badge-tag badge-gemini">Google GenAI SDK</span>
        </div>
        <p style="font-size: 7.8pt; margin: 0;">Powers our multimodal document ingestion pipeline. Sub-second visual parsing speed, ultra-low token cost, and native comprehension of complex Indian financial documents (Form 16 Part A/B, payslip tables, bank statements with UPI tags).</p>
      </div>
      <div class="arch-box">
        <div class="arch-box-title">
          <span>Google AI Studio</span>
          <span class="badge-tag badge-gemini">Prompt Engineering</span>
        </div>
        <p style="font-size: 7.8pt; margin: 0;">Source of truth for production prompts and JSON schemas (<span class="code-cell">ai_studio/</span>). Locked system instructions, few-shot prompt libraries, and strict Pydantic JSON schemas tested in AI Studio and imported verbatim into code.</p>
      </div>
      <div class="arch-box">
        <div class="arch-box-title">
          <span>Google Agent Development Kit (ADK)</span>
          <span class="badge-tag badge-adk">Multi-Agent Core</span>
        </div>
        <p style="font-size: 7.8pt; margin: 0;">Orchestrates our multi-agent architecture. Coordinates tool execution, session context passing, and conversational state machines across Money Finder, Leak Fixer, and Consultant agents with built-in telemetry.</p>
      </div>
      <div class="arch-box">
        <div class="arch-box-title">
          <span>Google Agent Skills (SKILL.md)</span>
          <span class="badge-tag badge-adk">Standardized Skills</span>
        </div>
        <p style="font-size: 7.8pt; margin: 0;">Implements standard <span class="code-cell">agentskills.io</span> declarative packaging. 9 discrete domain skills (tax regime, PF transfers, UPI AutoPay, etc.) loaded dynamically by agents with explicit instructions and execution constraints.</p>
      </div>
    </div>
  </div>

  <div class="doc-footer">
    <span>Paisa Pilot · Confidential · Google Startup Buildathon India 2026</span>
    <span>Page 2 of 4</span>
  </div>
</div>

<!-- ================= PAGE 3 ================= -->
<div class="page">
  <div>
    <div class="doc-header">
      <div class="logo">
        <span>PAISA PILOT</span>
        <span class="badge">Agent System & Code Inventory</span>
      </div>
      <div class="tagline">Detailed Agent Specifications & Repository Mapping</div>
    </div>

    <h2>6. Complete Multi-Agent System & Folder Mapping</h2>
    <p style="font-size: 8.2pt;">Paisa Pilot operates a specialized multi-agent network where each agent has strict responsibilities, sandboxed tools, and zero ability to invent numbers:</p>

    <table>
      <thead>
        <tr>
          <th>Agent Name</th>
          <th>Code Location</th>
          <th>Role, Tools & Capabilities</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Blur-Proof Vision Agent</strong></td>
          <td><span class="code-cell">llm/image_enhancer.py</span><br><span class="code-cell">llm/reader.py</span></td>
          <td>
            <strong>Job:</strong> Rescues blurry, poorly lit smartphone scans.<br>
            <strong>Tools:</strong> Pillow auto-contrast, unsharp mask filter, EXIF correction, Gemini 2.5 multimodal OCR.<br>
            <strong>Feature:</strong> Deductive Arithmetic Recovery — if a crease blurs Basic Pay, recovers it via <span class="code-cell">Gross - Sum(Allowances)</span>.
          </td>
        </tr>
        <tr>
          <td><strong>Money Finder Agent</strong></td>
          <td><span class="code-cell">agents/money_finder.py</span><br><span class="code-cell">skills/money-finder/</span></td>
          <td>
            <strong>Job:</strong> Uncovers all unclaimed, forgotten, or overpaid money.<br>
            <strong>Tools:</strong> Wraps <span class="code-cell">rules_engine/tax.py</span>, <span class="code-cell">pf.py</span>, <span class="code-cell">ais.py</span>, <span class="code-cell">refund_hunter.py</span>.<br>
            <strong>Output:</strong> 4 prioritized cards (Regime Switch, Extra TDS, Old PF, Refund Hunter) with computed annual/one-time split.
          </td>
        </tr>
        <tr>
          <td><strong>Leak Fixer Agent</strong></td>
          <td><span class="code-cell">agents/leak_fixer.py</span><br><span class="code-cell">skills/leak-fixer/</span></td>
          <td>
            <strong>Job:</strong> Audits transactions to stop recurring financial leaks.<br>
            <strong>Tools:</strong> Wraps <span class="code-cell">rules_engine/leaks.py</span> and <span class="code-cell">loans.py</span>.<br>
            <strong>Capabilities:</strong> Detects UPI AutoPay mandates, identifies recurring SaaS/gym subscriptions, calculates EMI refinancing savings.
          </td>
        </tr>
        <tr>
          <td><strong>AI Financial Consultant</strong></td>
          <td><span class="code-cell">agents/consultant.py</span><br><span class="code-cell">skills/tax-consultant/</span></td>
          <td>
            <strong>Job:</strong> Bilingual conversational copilot (English & Hindi).<br>
            <strong>Tools:</strong> Wraps <span class="code-cell">rules_engine/fd_sip.py</span>, <span class="code-cell">savings.py</span>, <span class="code-cell">salary.py</span>.<br>
            <strong>Capabilities:</strong> Explains salary payslips and tax deductions in plain language, calculates exact compound interest for goals (3, 5, 10 years).
          </td>
        </tr>
        <tr>
          <td><strong>CA Assistant / Checkup Agent</strong></td>
          <td><span class="code-cell">agents/ca_assistant.py</span><br><span class="code-cell">skills/ca-deductions/</span></td>
          <td>
            <strong>Job:</strong> Prepares the comprehensive Chartered Accountant filing pack.<br>
            <strong>Tools:</strong> Wraps <span class="code-cell">rules_engine/ca_checkup.py</span> and <span class="code-cell">itr.py</span>.<br>
            <strong>Output:</strong> Recommends likely ITR form (ITR-1 vs ITR-2), calculates deduction break-even thresholds, generates downloadable CA Action Plan.
          </td>
        </tr>
        <tr>
          <td><strong>Provenance & SEBI Guardrail Agent</strong></td>
          <td><span class="code-cell">agents/guardrail.py</span><br><span class="code-cell">agents/provenance.py</span></td>
          <td>
            <strong>Job:</strong> Security, compliance, and hallucination interceptor.<br>
            <strong>Rules:</strong> Blocks specific stock/crypto advice (enforces broad categories like Index Funds/FD only). Verifies every rupee in agent text exists in engine output.
          </td>
        </tr>
      </tbody>
    </table>

    <h2>7. Agent Skills Package Structure (<span class="code-cell">skills/</span>)</h2>
    <div class="grid-3">
      <div class="card">
        <h3>Tax & Deductions</h3>
        <div class="key-bullet"><span class="code-cell">skills/tax-regime/</span>: Old vs New regime framework.</div>
        <div class="key-bullet"><span class="code-cell">skills/tds/</span>: 26AS & AIS tax credit playbook.</div>
        <div class="key-bullet"><span class="code-cell">skills/ca-deductions/</span>: 80C, 80D, 80CCD, HRA limits.</div>
      </div>
      <div class="card">
        <h3>PF & Refunds</h3>
        <div class="key-bullet"><span class="code-cell">skills/pf-transfer/</span>: EPFO Form 13 transfer guide.</div>
        <div class="key-bullet"><span class="code-cell">skills/refunds/</span>: RBI failed UPI chargeback dispute.</div>
        <div class="key-bullet"><span class="code-cell">skills/ca-filing-playbook/</span>: Form readiness check.</div>
      </div>
      <div class="card">
        <h3>Leaks & Guardrails</h3>
        <div class="key-bullet"><span class="code-cell">skills/upi-autopay/</span>: NPCI mandate revocation.</div>
        <div class="key-bullet"><span class="code-cell">skills/savings-basics/</span>: 6-month emergency buffer.</div>
        <div class="key-bullet"><span class="code-cell">skills/money-guardrails/</span>: SEBI advice compliance.</div>
      </div>
    </div>

    <h2>8. Deterministic Rules Engine Inventory (<span class="code-cell">rules_engine/</span>)</h2>
    <div class="grid-2">
      <div class="card" style="font-size: 7.8pt;">
        <div><strong><span class="code-cell">rules_engine/tax.py</span></strong>: FY 2025-26 slabs, Section 87A rebate, standard deduction ₹75K.</div>
        <div><strong><span class="code-cell">rules_engine/pf.py</span></strong>: Inactive account compound interest decay & taxability after 3 years.</div>
        <div><strong><span class="code-cell">rules_engine/ais.py</span></strong>: Compares employer Form 16 TDS against IT Department AIS ledger.</div>
        <div><strong><span class="code-cell">rules_engine/leaks.py</span></strong>: Regex + date frequency analysis for recurring debit cadence.</div>
      </div>
      <div class="card" style="font-size: 7.8pt;">
        <div><strong><span class="code-cell">rules_engine/loans.py</span></strong>: Reducing balance EMI formula, foreclosure charges & net saving.</div>
        <div><strong><span class="code-cell">rules_engine/refund_hunter.py</span></strong>: Double-charge & failed transaction delta matching.</div>
        <div><strong><span class="code-cell">rules_engine/fd_sip.py</span></strong>: Periodic compound interest formula for SIP, RD, and FD goals.</div>
        <div><strong><span class="code-cell">rules_engine/config.py</span></strong>: Loads versioned YAML rules (<span class="code-cell">config/rules/fy2025-26.yaml</span>).</div>
      </div>
    </div>
  </div>

  <div class="doc-footer">
    <span>Paisa Pilot · Confidential · Google Startup Buildathon India 2026</span>
    <span>Page 3 of 4</span>
  </div>
</div>

<!-- ================= PAGE 4 ================= -->
<div class="page">
  <div>
    <div class="doc-header">
      <div class="logo">
        <span>PAISA PILOT</span>
        <span class="badge">Business Strategy & Demo</span>
      </div>
      <div class="tagline">Go-To-Market, Monetization & Evaluation Criteria</div>
    </div>

    <h2>9. Business Model & Monetization Strategy</h2>
    <div class="grid-3">
      <div class="card stat-card" style="text-align: left; padding: 8px;">
        <h3 class="coral-text" style="margin-top: 0;">1. Success Fee (B2C)</h3>
        <p style="font-size: 7.8pt; margin: 0;"><strong>Pay Only When You Win:</strong> 5% to 10% fee on actual, verified tax refunds or recovered dormant PF accounts. Zero upfront cost creates virality and instant user trust.</p>
      </div>
      <div class="card stat-card" style="text-align: left; padding: 8px;">
        <h3 class="teal-text" style="margin-top: 0;">2. Corporate Wellness (B2B)</h3>
        <p style="font-size: 7.8pt; margin: 0;"><strong>SaaS for Employers:</strong> ₹49/employee/month enterprise subscription. Companies offer Paisa Pilot to employees during tax declaration season (Form 12BB) to optimize payroll TDS.</p>
      </div>
      <div class="card stat-card" style="text-align: left; padding: 8px;">
        <h3 class="amber-text" style="margin-top: 0;">3. CA Partner Network</h3>
        <p style="font-size: 7.8pt; margin: 0;"><strong>Marketplace Revenue:</strong> Complex cases (capital gains, business revenue, foreign RSUs) referred to verified Chartered Accountants with our pre-compiled CA Action Plan for a 20% commission.</p>
      </div>
    </div>

    <h2>10. Market Opportunity & Sizing (India)</h2>
    <div class="grid-3">
      <div class="card">
        <div style="font-size: 13pt; font-weight: 800; color: #14152E;">$3.8 Billion</div>
        <div style="font-size: 7pt; font-weight: 700; color: #5F6577; text-transform: uppercase;">TAM (Total Addressable)</div>
        <p style="font-size: 7.5pt; margin-top: 2px;">120M+ salaried tax-paying individuals and formal sector employees across urban India.</p>
      </div>
      <div class="card">
        <div style="font-size: 13pt; font-weight: 800; color: #14152E;">$940 Million</div>
        <div style="font-size: 7pt; font-weight: 700; color: #5F6577; text-transform: uppercase;">SAM (Serviceable)</div>
        <p style="font-size: 7.5pt; margin-top: 2px;">35M+ tech, finance, and corporate employees actively switching jobs and filing returns online.</p>
      </div>
      <div class="card">
        <div style="font-size: 13pt; font-weight: 800; color: #E23D43;">$45 Million</div>
        <div style="font-size: 7pt; font-weight: 700; color: #5F6577; text-transform: uppercase;">SOM (Year 1-2 Target)</div>
        <p style="font-size: 7.5pt; margin-top: 2px;">1.5M active users via corporate payroll partnerships and viral consumer referral campaigns.</p>
      </div>
    </div>

    <h2>11. 60-Second Competition Pitch & Live Demo Script</h2>
    <div class="card" style="background: #FFFBEB; border: 1px solid #FDE68A; margin-bottom: 8px;">
      <p style="font-size: 8.2pt; margin: 0; line-height: 1.4;">
        <strong>The Demo Hook (Persona: Riya Sharma, 10 LPA Software Engineer):</strong><br>
        <em>"Judges, watch this 60-second screen. In 1 tap with sample data, Paisa Pilot analyzes Riya's payslip, Form 16, and bank statement:</em><br>
        • <strong>₹2,13,700 Found:</strong> ₹31,200 saved by switching tax regimes, ₹71,200 reclaimable AIS tax credit, and ₹1,11,300 across 2 dormant PF accounts.<br>
        • <strong>The Proof:</strong> Tap any card — notice the exact formula, inputs used, and official EPFO/Govt gazette link.<br>
        • <strong>₹648/Month Stopped:</strong> Discovers an active Fitzone Gym AutoPay and an idle CloudNotes subscription, generating an instant UPI revocation draft."
      </p>
    </div>

    <h2>12. Key Investor & Judge Q&A Cheat Sheet</h2>
    <div class="grid-2">
      <div class="card" style="font-size: 7.8pt;">
        <strong>Q: Why not just use ChatGPT or Gemini directly?</strong><br>
        <span style="color: #5F6577;">ChatGPT hallucinates tax rates, confuses New vs Old regime limits, and invents numbers that look plausible. Paisa Pilot uses Gemini only for visual reading, while deterministic Python code computes the math and guarantees provenance.</span>
      </div>
      <div class="card" style="font-size: 7.8pt;">
        <strong>Q: If people still need a CA, why use Paisa Pilot?</strong><br>
        <span style="color: #5F6577;">For 80% of routine salaried issues (tax regime, PF transfers, UPI leaks), users don't need a CA. For complex cases (capital gains/ESOPs), our CA Action Plan cuts prep time from 2 hours to 2 minutes, making CAs our partners.</span>
      </div>
      <div class="card" style="font-size: 7.8pt;">
        <strong>Q: How do you handle privacy and sensitive financial data?</strong><br>
        <span style="color: #5F6577;">Zero-Knowledge design: uploaded documents auto-delete from Google Cloud Storage within 24 hours via automated lifecycle rules. Users can delete all session data with 1 click. We never move money or file without consent.</span>
      </div>
      <div class="card" style="font-size: 7.8pt;">
        <strong>Q: What makes this uniquely enabled by Google Cloud?</strong><br>
        <span style="color: #5F6577;">Gemini 2.5 Flash Lite provides sub-second multimodal vision needed for crumpled phone scans at near-zero cost. Google ADK coordinates our agent network, and Cloud Run scales to zero for zero idle hosting expenses.</span>
      </div>
    </div>
  </div>

  <div class="doc-footer">
    <span>Paisa Pilot · Confidential · Google Startup Buildathon India 2026</span>
    <span>Page 4 of 4</span>
  </div>
</div>

</body>
</html>
"""

def main():
    html_path = os.path.abspath("paisa_pilot_pitch_deck.html")
    pdf_path = os.path.abspath("paisa-pilot-pitch-deck.pdf")
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)
    print(f"HTML pitch deck written to {html_path}")

    # Render via headless Chrome
    tmp_user_dir = "/tmp/chrome_pdf_pitch_tmp"
    cmd = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        f"--user-data-dir={tmp_user_dir}",
        f"--print-to-pdf={pdf_path}",
        "--no-pdf-header-footer",
        html_path
    ]

    print("Executing Chrome headless PDF render...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error rendering PDF: {result.stderr}", file=sys.stderr)
        sys.exit(result.returncode)

    if os.path.exists(pdf_path):
        size_kb = os.path.getsize(pdf_path) / 1024
        print(f"SUCCESS: Generated PDF at {pdf_path} ({size_kb:.1f} KB)")
    else:
        print("ERROR: PDF file not found after Chrome execution.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
