import { useEffect, useState } from "react";
import { getPortfolio, getRiskRollup, type PortfolioData, type RiskRollup } from "../api/client";
import { LoadingSpinner, ErrorMessage, EmptyState } from "../components/UI";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

export default function PortfolioSummary() {
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [rollup, setRollup] = useState<RiskRollup | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getPortfolio(), getRiskRollup()])
      .then(([p, r]) => {
        setPortfolio(p);
        setRollup(r);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;
  if (!portfolio) return <EmptyState message="No portfolio data available." />;

  const chartData = rollup
    ? [
        { name: "Critical", count: rollup.critical, fill: "#dc2626" },
        { name: "High", count: rollup.high, fill: "#ea580c" },
        { name: "Medium", count: rollup.medium, fill: "#d97706" },
        { name: "Low", count: rollup.low, fill: "#2563eb" },
      ]
    : [];

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Portfolio Summary</h2>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-card rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-muted uppercase tracking-wide">Repositories</p>
          <p className="text-2xl font-bold mt-1">{portfolio.total_repositories}</p>
        </div>
        <div className="bg-card rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-muted uppercase tracking-wide">Total Findings</p>
          <p className="text-2xl font-bold mt-1">{portfolio.total_findings}</p>
        </div>
        <div className="bg-card rounded-lg border border-gray-200 p-4">
          <p className="text-xs text-muted uppercase tracking-wide">Critical + High</p>
          <p className="text-2xl font-bold mt-1 text-red-600">
            {(portfolio.severity.critical ?? 0) + (portfolio.severity.high ?? 0)}
          </p>
        </div>
      </div>

      {/* Severity chart */}
      {chartData.length > 0 && (
        <div className="bg-card rounded-lg border border-gray-200 p-4 mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Severity Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Repository table */}
      {portfolio.repositories.length > 0 && (
        <div className="bg-card rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Repository</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Latest Gate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {portfolio.repositories.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{r.name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        r.latest_gate_result === "pass"
                          ? "bg-green-100 text-green-700"
                          : r.latest_gate_result === "warn"
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {r.latest_gate_result}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
