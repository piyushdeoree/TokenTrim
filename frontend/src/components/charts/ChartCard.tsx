import { ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
// Chart panels use the theme "chart" colour (#467770 light / #26344A dark) as the surface; series use the button yellow for contrast.
const SERIES = '#FBCB48', TICK = { fill: '#ffffff', fontSize: 12 };
export function ChartCard({ title, data, x, y, kind = 'line' }: { title: string; data: object[]; x: string; y: string; kind?: 'line' | 'bar' }) {
  const common = (<><CartesianGrid strokeDasharray="3 3" stroke="#ffffff" opacity={0.2} /><XAxis dataKey={x} tick={TICK} stroke="#ffffff" /><YAxis tick={TICK} stroke="#ffffff" />
    <Tooltip contentStyle={{ background: '#171919', border: 'none', color: '#fff' }} labelStyle={{ color: '#fff' }} /></>);
  return (
    <section className="rounded-lg bg-chart p-5 text-white">
      <h2 className="mb-3 text-base font-semibold">{title}</h2>
      <div className="h-56" role="img" aria-label={`${title} chart`}>
        <ResponsiveContainer width="100%" height="100%">
          {kind === 'line'
            ? <LineChart data={data}>{common}<Line type="monotone" dataKey={y} stroke={SERIES} strokeWidth={2} dot={false} /></LineChart>
            : <BarChart data={data}>{common}<Bar dataKey={y} fill={SERIES} /></BarChart>}
        </ResponsiveContainer>
      </div>
    </section>
  );
}
