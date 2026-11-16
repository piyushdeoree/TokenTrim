import { ReactNode } from 'react';
export type Col<T> = { header: string; cell: (r: T) => ReactNode };
export function DataTable<T extends { id?: string | number }>({ rows, cols, caption }: { rows: T[]; cols: Col<T>[]; caption: string }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
      <table className="w-full text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-slate-100 dark:bg-slate-800"><tr>{cols.map((c) => <th key={c.header} scope="col" className="px-3 py-2 font-semibold">{c.header}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={r.id ?? i} className="border-t border-slate-200 dark:border-slate-700">{cols.map((c) => <td key={c.header} className="px-3 py-2">{c.cell(r)}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}
