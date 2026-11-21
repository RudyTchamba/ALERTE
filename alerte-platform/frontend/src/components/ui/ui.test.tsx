import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Providers } from '@/app/providers'
import { axeViolations } from '@/test/utils'
import { Badge, Button, Dialog, Field, Input, ProgressBar, StatusBadge, Table, TBody, Td, Th, THead, Tr, Tabs, ToastProvider, useToast } from '.'

const wrap = (ui: React.ReactElement) => render(<Providers>{ui}</Providers>)

describe('ui primitives', () => {
  it('Button: loading disables it and sets aria-busy', () => {
    wrap(<Button loading>Save</Button>)
    const b = screen.getByRole('button', { name: /save/i })
    expect(b).toBeDisabled()
    expect(b).toHaveAttribute('aria-busy', 'true')
  })

  it('Field wires label, hint and error to the control', () => {
    wrap(<Field label="Name" hint="Your name" error="Required" required><Input /></Field>)
    const input = screen.getByLabelText(/name/i)
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAccessibleDescription(/your name.*required/i)
    expect(screen.getByRole('alert')).toHaveTextContent('Required')
  })

  it('status badges always carry a text label (colour is never alone)', () => {
    wrap(<><StatusBadge status="not_verified" /><StatusBadge status="running" /><Badge tone="danger">Failed</Badge></>)
    expect(screen.getByText('not verified')).toBeInTheDocument()
    expect(screen.getByText('running')).toBeInTheDocument()
    expect(screen.getByText('Failed').querySelector('svg')).toHaveAttribute('aria-hidden', 'true')
  })

  it('Tabs: arrow keys move selection and focus (roving tabindex)', async () => {
    const user = userEvent.setup()
    function T() {
      const [v, setV] = useState('a')
      return <Tabs label="demo" value={v} onChange={setV} tabs={[{ id: 'a', label: 'A', content: 'panel A' }, { id: 'b', label: 'B', content: 'panel B' }]} />
    }
    wrap(<T />)
    const a = screen.getByRole('tab', { name: 'A' })
    a.focus()
    await user.keyboard('{ArrowRight}')
    expect(screen.getByRole('tab', { name: 'B' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'B' })).toHaveFocus()
    expect(screen.getByRole('tabpanel')).toHaveTextContent('panel B')
    expect(screen.getByRole('tab', { name: 'A' })).toHaveAttribute('tabindex', '-1')
  })

  it('Dialog: traps focus, closes on Escape and restores focus to the opener', async () => {
    const user = userEvent.setup()
    function D() {
      const [open, setOpen] = useState(false)
      return <><button onClick={() => setOpen(true)}>open</button><Dialog open={open} onClose={() => setOpen(false)} title="Confirm"><button>inside</button></Dialog></>
    }
    wrap(<D />)
    const opener = screen.getByRole('button', { name: 'open' })
    await user.click(opener)
    const dlg = screen.getByRole('dialog', { name: 'Confirm' })
    expect(dlg).toHaveAttribute('aria-modal', 'true')
    await user.tab(); await user.tab(); await user.tab()
    expect(dlg.contains(document.activeElement)).toBe(true)
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(opener).toHaveFocus()
  })

  it('ProgressBar exposes progressbar semantics', () => {
    wrap(<ProgressBar pct={42.4} label="Ingesting" />)
    expect(screen.getByRole('progressbar', { name: 'Ingesting' })).toHaveAttribute('aria-valuenow', '42')
  })

  it('toasts are announced politely (status) and errors assertively (alert)', async () => {
    const user = userEvent.setup()
    function P() { const t = useToast(); return <><button onClick={() => t.push('saved', 'ok')}>ok</button><button onClick={() => t.push('broken', 'danger')}>bad</button></> }
    render(<Providers><ToastProvider><P /></ToastProvider></Providers>)
    await user.click(screen.getByText('ok')); await user.click(screen.getByText('bad'))
    expect(screen.getByText('saved').closest('[role=status]')).toBeTruthy()
    expect(screen.getByText('broken').closest('[role=alert]')).toBeTruthy()
  })

  it('a captioned table with column headers has no axe violation', async () => {
    const { container } = wrap(
      <Table caption="Items"><THead><Tr><Th>Name</Th></Tr></THead><TBody><Tr><Td>x</Td></Tr></TBody></Table>,
    )
    expect(within(container).getByRole('table', { name: 'Items' })).toBeInTheDocument()
    expect(await axeViolations(container)).toEqual([])
  })

  it('a form made of Fields has no axe violation', async () => {
    const { container } = wrap(<form><Field label="A"><Input /></Field><Field label="B" error="bad"><Input /></Field><Button type="submit" onClick={vi.fn()}>Go</Button></form>)
    expect(await axeViolations(container)).toEqual([])
  })
})
