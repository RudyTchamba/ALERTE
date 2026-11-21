/** Comma/newline separated text <-> string[] for simple "list" form fields. */
export const splitList = (s: string | undefined | null): string[] =>
  (s ?? '').split(/[,\n]/).map((x) => x.trim()).filter(Boolean)
export const joinList = (a: string[] | null | undefined): string => (a ?? []).join(', ')
