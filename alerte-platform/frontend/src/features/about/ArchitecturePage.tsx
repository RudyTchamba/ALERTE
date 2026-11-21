import { useTranslation } from 'react-i18next'
import { Badge, PageHeader, Table, TBody, Td, Th, THead, Tr } from '@/components/ui'

/** Static mapping of ITU-T Y.3172 architecture components to ALERTE modules (hackathon criterion C5). */
const ROWS: { y: string; module: string; where: string }[] = [
  { y: 'ML pipeline — Source / Collector', module: 'knowledge (document upload, import of archives)', where: '/studio/knowledge' },
  { y: 'ML pipeline — Preprocessor', module: 'knowledge (extraction, OCR, chunking, quality report)', where: '/studio/knowledge' },
  { y: 'ML pipeline — Model (ML function)', module: 'agents (model profiles, tools, prompts)', where: '/studio/agents' },
  { y: 'ML pipeline — Policy', module: 'mandates (registry of powers and duties) + knowledge access rights', where: '/studio/countries' },
  { y: 'ML pipeline — Distributor / Sink', module: 'simulation (coordination board, decisions) → gaps → reports', where: '/room' },
  { y: 'ML Sandbox', module: 'simulation (frozen snapshot, scripted / cassette / real-model runs)', where: '/studio/exercises' },
  { y: 'ML Intent', module: 'scenarios (injects, demands, injected faults, readiness checks)', where: '/studio/scenarios' },
  { y: 'ML Function Orchestrator (MLFO)', module: 'simulation (state machine, runner, facilitator commands)', where: '/room' },
  { y: 'Management: logging, monitoring, traceability', module: 'audit (hash-chained ledger, verification, replay, decision trace)', where: '/audit' },
  { y: 'Management: evaluation and KPIs', module: 'evaluation (T1–T6, 13-dimension scorecard)', where: '/evaluation' },
  { y: 'Management: reporting', module: 'reports (versioned, PDF / Markdown / JSON / CSV / XLSX)', where: '/reports' },
]

export function ArchitecturePage() {
  const { t } = useTranslation()
  return (
    <>
      <PageHeader title={t('about.title')} description={t('about.description')} />
      <Table caption={t('about.title')}>
        <THead><Tr><Th>{t('about.y3172')}</Th><Th>{t('about.module')}</Th><Th>{t('about.screen')}</Th></Tr></THead>
        <TBody>{ROWS.map((r) => <Tr key={r.y}><Td>{r.y}</Td><Td>{r.module}</Td><Td><a href={r.where}>{r.where}</a></Td></Tr>)}</TBody>
      </Table>
      <p className="mt-3 text-sm"><Badge tone="warn">{t('about.noteLabel')}</Badge> {t('about.note')}</p>
    </>
  )
}
