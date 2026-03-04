interface Props {
  title: string;
  value: number | string;
  subtitle?: string;
}

export default function StatCard({ title, value, subtitle }: Props) {
  return (
    <div className="bg-white rounded-lg shadow p-5">
      <p className="text-sm text-gray-500">{title}</p>
      <p className="text-3xl font-bold text-mtp-blue mt-1">{value}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  );
}
