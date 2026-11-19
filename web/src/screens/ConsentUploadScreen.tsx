import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/Button'
import { Link } from 'react-router-dom'
import { track } from '../lib/track'
import { Icon } from '../components/Icon'
import { Wordmark } from '../components/Logo'
import { api, ApiError } from '../lib/api'
import { useApp } from '../state/AppContext'

const DOCUMENT_TYPES = [
  { type: 'payslip', labelKey: 'upload.payslip' as const, icon: 'file' },
  { type: 'form16', labelKey: 'upload.form16' as const, icon: 'receipt' },
  { type: 'bank_statement', labelKey: 'upload.bankStatement' as const, icon: 'bank' },
  { type: 'pf_passbook', labelKey: 'upload.pfPassbook' as const, icon: 'book' },
  { type: 'ais', labelKey: 'upload.ais' as const, icon: 'chart' },
] as const

export function ConsentUploadScreen() {
  const { t, language, setLanguage, sessionId, setSessionId, setSampleData } = useApp()
  const navigate = useNavigate()
  const [consentChecked, setConsentChecked] = useState(false)
  const [consenting, setConsenting] = useState(false)
  const [samplingLoading, setSamplingLoading] = useState(false)
  const [uploadedKeys, setUploadedKeys] = useState<Record<string, string>>({})
  const [uploadingType, setUploadingType] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleContinue() {
    setConsenting(true)
    setError(null)
    try {
      const { session_id } = await api.giveConsent(true)
      setSessionId(session_id)
      setSampleData(false)
      track('consent_given')
    } catch {
      setError('Could not start a session. Please try again.')
    } finally {
      setConsenting(false)
    }
  }

  async function handleTrySample() {
    setSamplingLoading(true)
    setError(null)
    try {
      const result = await api.createSampleSession()
      setSessionId(result.session_id)
      setSampleData(true)
      track('sample_started')
      navigate('/app/home')
    } catch {
      setError('Could not load sample data. Please try again.')
    } finally {
      setSamplingLoading(false)
    }
  }

  async function handleUpload(documentType: string, file: File) {
    if (!sessionId) return
    setUploadingType(documentType)
    setError(null)
    try {
      const { upload_key } = await api.uploadDocument(sessionId, documentType, file)
      setUploadedKeys((prev) => ({ ...prev, [documentType]: upload_key }))
      const readResult = await api.readDocument(sessionId, documentType, upload_key)
      track('document_uploaded', documentType)
      navigate(`/app/confirm/${documentType}`, { state: { readResult } })
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Upload failed. Please try again.')
      setUploadedKeys((prev) => {
        const { [documentType]: _removed, ...rest } = prev
        return rest
      })
    } finally {
      setUploadingType(null)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col gap-6 px-5 py-8 md:max-w-lg">
      <div className="flex items-center justify-between">
        <Wordmark />
        <button
          onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
          className="text-muted border-line min-h-11 rounded-full border px-3 text-sm font-semibold"
        >
          {t('common.language')}
        </button>
      </div>

      {!sessionId && (
        <div className="animate-card-entrance border-line rounded-[20px] border bg-white p-6">
          <h1 className="text-navy text-2xl font-extrabold">{t('consent.title')}</h1>
          <p className="text-muted mt-3 text-sm leading-relaxed">{t('consent.body')}</p>
          <p className="text-muted mt-2 text-xs">
            <Link to="/privacy" className="underline">Privacy</Link> · <Link to="/terms" className="underline">Terms</Link>
          </p>

          <label className="mt-5 flex min-h-11 items-start gap-3 text-sm">
            <input
              type="checkbox"
              checked={consentChecked}
              onChange={(e) => setConsentChecked(e.target.checked)}
              className="mt-0.5 h-5 w-5 shrink-0 accent-[#2EC4B6]"
            />
            <span className="text-navy font-medium">{t('consent.checkbox')}</span>
          </label>

          <Button
            variant="primary"
            className="mt-5 w-full"
            disabled={!consentChecked}
            loading={consenting}
            onClick={handleContinue}
          >
            {t('consent.continue')}
          </Button>

          <div className="border-line my-5 border-t" />

          <p className="text-muted text-sm">{t('consent.tryWithSampleHint')}</p>
          <Button variant="outline" className="mt-3 w-full" loading={samplingLoading} onClick={handleTrySample}>
            {t('consent.tryWithSample')}
          </Button>
        </div>
      )}

      {sessionId && (
        <div className="animate-card-entrance border-line rounded-[20px] border bg-white p-6">
          <h2 className="text-navy text-xl font-bold">{t('consent.uploadTitle')}</h2>
          <p className="text-muted mt-1 text-sm">{t('consent.uploadHint')}</p>

          <div className="mt-5 flex flex-col gap-3">
            {DOCUMENT_TYPES.map((doc) => (
              <div key={doc.type} className="border-line flex items-center justify-between gap-3 rounded-2xl border p-3">
                <div className="flex items-center gap-3">
                  <span className="bg-icon-tile text-coral-dark flex h-10 w-10 items-center justify-center rounded-xl"><Icon name={doc.icon} size={20} /></span>
                  <span className="text-navy text-sm font-semibold">{t(doc.labelKey)}</span>
                </div>
                {uploadedKeys[doc.type] ? (
                  <span className="text-teal text-sm font-semibold">✓ {t('upload.uploaded')}</span>
                ) : (
                  <label className="bg-coral-button text-navy inline-flex min-h-11 cursor-pointer items-center whitespace-nowrap rounded-[18px] px-3 text-sm font-semibold sm:px-4">
                    {uploadingType === doc.type ? t('common.loading') : t('upload.choose')}
                    <input
                      type="file"
                      accept="application/pdf,image/*"
                      className="hidden"
                      disabled={uploadingType !== null}
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) handleUpload(doc.type, file)
                      }}
                    />
                  </label>
                )}
              </div>
            ))}
          </div>
          {uploadingType && (
            <p className="text-muted mt-4 text-sm" role="status" aria-live="polite">
              {t('upload.reading')}
            </p>
          )}
        </div>
      )}

      {error && <p className="text-sm font-medium text-[#C0392B]">{error}</p>}
    </div>
  )
}
