import { useNavigate } from 'react-router-dom'

/** Shown on the Confirm screen when the reader could not read the document
 * clearly (blurry photo, cropped page, nothing found). */
export function ReadWarning({ warnings, nothingRead }: { warnings: string[]; nothingRead: boolean }) {
  const navigate = useNavigate()
  if (!nothingRead && warnings.length === 0) return null
  return (
    <div className="bg-warning-card border-yellow mt-4 rounded-2xl border p-4" role="alert">
      <p className="text-navy text-sm font-bold">
        {nothingRead ? 'We could not read this document clearly.' : 'Please double-check these values.'}
      </p>
      {warnings.length > 0 && (
        <ul className="text-navy mt-1 list-disc pl-5 text-sm">
          {warnings.slice(0, 3).map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
      <p className="text-muted mt-2 text-sm">
        {nothingRead
          ? 'Try a sharper, well-lit photo or the original PDF. You can also type the numbers in yourself.'
          : 'We were unsure about some of them. Anything highlighted below needs a look.'}
      </p>
      <button
        type="button"
        onClick={() => navigate('/app/consent')}
        className="text-navy mt-3 min-h-11 rounded-[18px] border-2 border-yellow bg-white px-4 text-sm font-semibold"
      >
        Upload a clearer copy
      </button>
    </div>
  )
}
