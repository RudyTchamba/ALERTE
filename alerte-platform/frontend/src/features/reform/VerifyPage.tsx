import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useSearchParams } from 'react-router-dom'
import { CircleCheck, CircleX, Printer, ShieldAlert, ShieldCheck } from 'lucide-react'
import { useApiQuery } from '@/api/hooks'
import type { ReformVerification } from '@/api/loose'
import { ErrorState, LoadingState } from '@/components/ui'
import { QrSvg } from '@/features/present/AudienceQR'
import { cn } from '@/lib/cn'
import { fmtDateTime } from '@/lib/format'

/**
 * Page PUBLIQUE `/verify/:sha` : le document (projet d'article) et sa vérification en direct.
 * Imprimée (`?print=1` ou bouton), elle devient le PDF : le QR code renvoie à cette même page.
 */
export function VerifyPage() {
  const { t } = useTranslation()
  const { sha = '' } = useParams()
  const [params] = useSearchParams()
  const q = useApiQuery<ReformVerification>(['reform-verify', sha], `/verify/reform/${sha}`)
  const ready = q.data?.found === true

  useEffect(() => {
    if (!ready || params.get('print') !== '1') return
    const id = window.setTimeout(() => window.print(), 400)
    return () => window.clearTimeout(id)
  }, [ready, params])

  return (
    <div className="min-h-screen bg-bg text-ink print:bg-white print:text-black">
      <main id="main" className="mx-auto max-w-3xl p-4 lg:p-8">
        {q.isPending ? <LoadingState /> : q.isError ? <ErrorState error={q.error} />
          : !q.data.found ? <p role="alert" className="mt-10 text-center text-lg">{t('reform.notFound')}</p>
          : <Doc v={q.data} />}
      </main>
    </div>
  )
}

function Check({ ok, label }: { ok: boolean; label: string }) {
  return <li className="flex items-start gap-2">{ok ? <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-ok" aria-hidden /> : <CircleX className="mt-0.5 h-4 w-4 shrink-0 text-danger" aria-hidden />}<span>{label}</span></li>
}

function Doc({ v }: { v: Extract<ReformVerification, { found: true }> }) {
  const { t } = useTranslation()
  const c = v.content, a = v.anchors
  const url = `${window.location.origin}/verify/${v.sha256}`
  return (
    <>
      {/* Bandeau de vérification (écran seulement) */}
      <section aria-label={t('reform.verifyTitle')} className={cn('mb-6 rounded-xl border-2 p-4 print:hidden', v.ok ? 'border-ok bg-oksoft' : 'border-danger bg-dangersoft')}>
        <p className={cn('flex items-center gap-2 text-lg font-black', v.ok ? 'text-ok' : 'text-danger')}>
          {v.ok ? <ShieldCheck className="h-6 w-6" aria-hidden /> : <ShieldAlert className="h-6 w-6" aria-hidden />}{v.ok ? t('reform.ok') : t('reform.ko')}
        </p>
        <ul className="mt-2 flex flex-col gap-1 text-sm">
          <Check ok={v.content_ok} label={t('reform.checks.content')} />
          <Check ok={v.ledger_ok} label={t('reform.checks.ledger', { n: v.ledger_checked ?? 0 })} />
          <Check ok={v.anchor_ok} label={t('reform.checks.anchor')} />
        </ul>
        <button type="button" onClick={() => window.print()} className="mt-3 inline-flex items-center gap-2 rounded-lg border border-line bg-surface px-3 py-1.5 text-sm font-semibold"><Printer className="h-4 w-4" aria-hidden />{t('reform.print')}</button>
      </section>

      {/* Le document */}
      <article className="rounded-xl border border-line bg-surface p-6 print:border-0 print:p-0">
        <header className="mb-6 flex items-start justify-between gap-6 border-b border-line pb-4 print:border-black">
          <div className="min-w-0">
            <p className="eyebrow text-brand print:text-black">{t('reform.docEyebrow')}</p>
            <h1 className="mt-1 text-2xl font-black tracking-tight">{c.title}</h1>
            <p className="mt-1 text-xs font-bold tracking-widest text-warn uppercase print:text-black">{t('reform.proposal')}</p>
          </div>
          <figure className="w-32 shrink-0 text-center">
            <QrSvg value={url} title={t('reform.scan')} className="w-full" />
            <figcaption className="mt-1 text-xs leading-tight text-muted print:text-black">{t('reform.scan')}</figcaption>
          </figure>
        </header>

        <p className="mb-4 text-sm"><strong>{t('reform.gap')} :</strong> {a.gap_code} — {a.gap_title}<br /><strong>{t('reform.exercise')} :</strong> {a.exercise_code ?? '—'}</p>

        <h2 className="text-lg font-bold">{c.article_label}</h2>
        <p className="mt-2 text-base leading-relaxed">{c.article_text}</p>

        <h2 className="mt-6 text-sm font-bold tracking-wide uppercase">{t('reform.motives')}</h2>
        <p className="mt-1 text-sm leading-relaxed">{c.explanation}</p>

        {c.citations.length > 0 && <>
          <h2 className="mt-6 text-sm font-bold tracking-wide uppercase">{t('reform.basis')}</h2>
          <ul className="mt-1 flex flex-col gap-1.5 text-sm">
            {c.citations.map((x) => <li key={x.chunk_id}><strong>{x.doc_code}{x.article ? `, ${x.article}` : ''}</strong> — « {x.quote} »</li>)}
          </ul>
        </>}
        {c.rejected_citations > 0 && <p className="mt-2 text-xs text-warn print:text-black">{t('reform.partial', { n: c.rejected_citations })}</p>}

        <footer className="mt-8 border-t border-line pt-3 font-mono text-xs leading-relaxed break-all text-muted print:border-black print:text-black">
          <p className="mb-1 font-sans text-xs font-bold tracking-wide uppercase">{t('reform.anchors')}</p>
          <p>{t('reform.ledgerHead', { seq: a.ledger_head_seq ?? '—' })} · {a.ledger_head_hash}</p>
          <p>{t('reform.snapshot')} · {a.snapshot_sha256 ?? '—'}</p>
          <p>{t('reform.fingerprint')} · {v.sha256}</p>
          <p>{t('reform.model')} · {v.model}{v.created_at ? ` · ${fmtDateTime(v.created_at)}` : ''}</p>
          <p className="mt-2 font-sans text-xs italic">{t('reform.disclaimer')}</p>
        </footer>
      </article>
    </>
  )
}
