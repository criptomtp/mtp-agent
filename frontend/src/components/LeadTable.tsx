interface Lead {
  id: string;
  name: string;
  email: string;
  phone: string;
  city: string;
  source: string;
  status: string;
  created_at: string;
}

interface Props {
  leads: Lead[];
  onSelect?: (lead: Lead) => void;
}

const statusColors: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  contacted: "bg-yellow-100 text-yellow-800",
  converted: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
};

export default function LeadTable({ leads, onSelect }: Props) {
  if (!leads.length) {
    return <p className="text-gray-400 text-center py-8">No leads found</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="pb-2 font-medium">Name</th>
            <th className="pb-2 font-medium">Email</th>
            <th className="pb-2 font-medium">City</th>
            <th className="pb-2 font-medium">Source</th>
            <th className="pb-2 font-medium">Status</th>
            <th className="pb-2 font-medium">Date</th>
          </tr>
        </thead>
        <tbody>
          {leads.map((lead) => (
            <tr
              key={lead.id}
              className="border-b hover:bg-gray-50 cursor-pointer"
              onClick={() => onSelect?.(lead)}
            >
              <td className="py-2 font-medium text-mtp-blue">{lead.name}</td>
              <td className="py-2 text-gray-600">{lead.email || "-"}</td>
              <td className="py-2 text-gray-600">{lead.city || "-"}</td>
              <td className="py-2 text-gray-600">{lead.source || "-"}</td>
              <td className="py-2">
                <span
                  className={`px-2 py-0.5 rounded-full text-xs ${
                    statusColors[lead.status] || "bg-gray-100 text-gray-600"
                  }`}
                >
                  {lead.status}
                </span>
              </td>
              <td className="py-2 text-gray-400">
                {new Date(lead.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
