import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PromptView, parsePrompt } from './PromptView'

const SAMPLE = `## 1. Role
You are Agent MET.
Instructions: 

## 3. Rules of conduct
- How to cite:
  1. Pick ONE <retrieved_document> block.
## 4. Tools
- search_kb: {"action":"search_kb","rationale":"...","query":"..."}  (query up to 300 characters)
- post: {"action":"post","to":"SEAT_CODE"}
  (to: another seat code)
## 5. Activation context (round 1)
Inject title: (inject title)`

describe('PromptView', () => {
  it('splits sections, steps and tool notes', () => {
    const s = parsePrompt(SAMPLE)
    expect(s.map((x) => x.n)).toEqual(['1', '3', '4', '5'])
    expect(s[1].lines[1]).toEqual({ kind: 'step', n: '1', text: 'Pick ONE <retrieved_document> block.' })
    expect(s[2].lines[1]).toMatchObject({ kind: 'item', notes: ['(to: another seat code)'] })
  })

  it('renders headings, pretty JSON and empty / template values', () => {
    render(<PromptView text={SAMPLE} />)
    expect(screen.getByRole('heading', { name: /Tools/ })).toBeInTheDocument()
    expect(screen.getByText(/"query": "\.\.\."/)).toBeInTheDocument()
    expect(screen.getByText('(inject title)')).toHaveClass('italic')
    expect(screen.getByText('—')).toBeInTheDocument()
  })
})
