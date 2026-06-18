import React from 'react';
import type { SummaryResponse } from '../types';
import { Database, Filter, AlertTriangle, FileSpreadsheet, CheckCircle, BarChart3 } from 'lucide-react';

interface CleaningSummaryProps {
  summary: SummaryResponse | null;
  isLoading: boolean;
}

export const CleaningSummary: React.FC<CleaningSummaryProps> = ({ summary, isLoading }) => {
  if (isLoading && !summary) {
    return (
      <div className="flex flex-col items-center justify-center p-12 border border-slate-800 rounded-xl bg-[#0f172a]/40">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-4 text-sm text-slate-400">Loading dataset summary metrics...</p>
      </div>
    );
  }

  if (!summary) return null;

  const { cleaning, abc_distribution, total_revenue } = summary;

  const formatRevenue = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(val).replace('$', '¤ ');
  };

  // Calculate percentages for ABC distribution bar
  const totalAbc = abc_distribution.total || 1;
  const pctA = (abc_distribution.A / totalAbc) * 100;
  const pctB = (abc_distribution.B / totalAbc) * 100;
  const pctC = (abc_distribution.C / totalAbc) * 100;

  const cleaningStats = [
    { label: 'Raw Sales Records', value: cleaning.rows_before.toLocaleString(), icon: Database, color: 'text-slate-400' },
    { label: 'Duplicate Rows Removed', value: cleaning.duplicates_removed.toLocaleString(), icon: Filter, color: 'text-blue-400', isDrop: true },
    { label: 'Admin "DUMMY" Dropped', value: cleaning.dummy_rows_removed.toLocaleString(), icon: AlertTriangle, color: 'text-amber-400', isDrop: true },
    { label: 'Group Income/Expense Dropped', value: cleaning.group_income_rows_removed.toLocaleString(), icon: AlertTriangle, color: 'text-orange-400', isDrop: true },
    { label: 'Returns Flagged (Kept)', value: cleaning.returns_flagged.toLocaleString(), icon: FileSpreadsheet, color: 'text-purple-400' },
    { label: 'Zero-Sales Flagged (Kept)', value: cleaning.zero_sales_flagged.toLocaleString(), icon: FileSpreadsheet, color: 'text-indigo-400' },
    { label: 'Data Anomalies Flagged (Kept)', value: cleaning.anomalies_flagged.toLocaleString(), icon: AlertTriangle, color: 'text-red-400' },
    { label: 'Cleaned Records Remaining', value: cleaning.rows_after.toLocaleString(), icon: CheckCircle, color: 'text-emerald-400', isSuccess: true },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-fade-in">
      {/* Column 1: Catalog Profile */}
      <div className="bg-[#0f172a]/60 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-xs flex flex-col justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4 pb-2 border-b border-slate-800/60 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            Catalog Profile
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-900/50 border border-slate-800/80 rounded-lg p-3">
              <span className="text-xs text-slate-500 font-semibold block uppercase">Total Products</span>
              <span className="text-2xl font-bold font-outfit text-slate-200">{cleaning.unique_articles.toLocaleString()}</span>
            </div>
            <div className="bg-slate-900/50 border border-slate-800/80 rounded-lg p-3">
              <span className="text-xs text-slate-500 font-semibold block uppercase">Active Shops</span>
              <span className="text-2xl font-bold font-outfit text-slate-200">{cleaning.unique_shops.toLocaleString()}</span>
            </div>
            <div className="bg-slate-900/50 border border-slate-800/80 rounded-lg p-3">
              <span className="text-xs text-slate-500 font-semibold block uppercase">Departments</span>
              <span className="text-2xl font-bold font-outfit text-slate-200">{cleaning.unique_departments.toLocaleString()}</span>
            </div>
            <div className="bg-slate-900/50 border border-slate-800/80 rounded-lg p-3">
              <span className="text-xs text-slate-500 font-semibold block uppercase">Total Revenue</span>
              <span className="text-xl font-bold font-outfit text-emerald-400 truncate block mt-0.5" title={formatRevenue(total_revenue)}>
                {formatRevenue(total_revenue)}
              </span>
            </div>
          </div>
        </div>

        <div className="mt-6 border-t border-slate-800/60 pt-4">
          <p className="text-xs text-slate-400 italic">
            Dataset loaded from server cache: <strong>{cleaning.rows_after.toLocaleString()}</strong> rows analyzed.
          </p>
        </div>
      </div>

      {/* Column 2: ABC revenue distribution */}
      <div className="bg-[#0f172a]/60 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-xs flex flex-col justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4 pb-2 border-b border-slate-800/60 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-blue-400" />
            ABC Product Distribution
          </h2>

          <p className="text-xs text-slate-400 mb-4">
            ABC classification ranks products by revenue: Class A (top 70%), Class B (70-90%), and Class C (90-100%).
          </p>

          {/* Combined Progress Bar */}
          <div className="h-6 w-full rounded-full bg-slate-900 border border-slate-800 overflow-hidden flex mb-5 shadow-inner">
            <div
              style={{ width: `${pctA}%` }}
              className="bg-gradient-to-r from-red-600 to-red-400 h-full transition-all duration-500"
              title={`Class A: ${abc_distribution.A} items (${pctA.toFixed(1)}%)`}
            ></div>
            <div
              style={{ width: `${pctB}%` }}
              className="bg-gradient-to-r from-amber-600 to-amber-400 h-full transition-all duration-500"
              title={`Class B: ${abc_distribution.B} items (${pctB.toFixed(1)}%)`}
            ></div>
            <div
              style={{ width: `${pctC}%` }}
              className="bg-gradient-to-r from-slate-600 to-slate-400 h-full transition-all duration-500"
              title={`Class C: ${abc_distribution.C} items (${pctC.toFixed(1)}%)`}
            ></div>
          </div>

          {/* Details Legend */}
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-xs bg-red-400"></span>
                <span className="text-slate-300">Class A (Top Sellers - 70%)</span>
              </div>
              <span className="text-slate-200">{abc_distribution.A.toLocaleString()} products ({pctA.toFixed(1)}%)</span>
            </div>
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-xs bg-amber-400"></span>
                <span className="text-slate-300">Class B (Strong Sellers - 20%)</span>
              </div>
              <span className="text-slate-200">{abc_distribution.B.toLocaleString()} products ({pctB.toFixed(1)}%)</span>
            </div>
            <div className="flex items-center justify-between text-xs font-semibold">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-xs bg-slate-400"></span>
                <span className="text-slate-300">Class C (Long Tail - 10%)</span>
              </div>
              <span className="text-slate-200">{abc_distribution.C.toLocaleString()} products ({pctC.toFixed(1)}%)</span>
            </div>
          </div>
        </div>

        <div className="mt-5 text-[11px] text-slate-500 bg-slate-950/40 p-2 rounded-lg border border-slate-900">
          * Note: Missing winners analysis checks Class A & B products only.
        </div>
      </div>

      {/* Column 3: Data Cleaning Report */}
      <div className="bg-[#0f172a]/60 border border-slate-800 rounded-xl p-5 shadow-lg backdrop-blur-xs">
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider mb-4 pb-2 border-b border-slate-800/60 flex items-center gap-2">
          <Database className="w-4 h-4 text-purple-400" />
          Data Quality Pipeline
        </h2>

        <div className="flex flex-col gap-2 text-xs">
          {cleaningStats.map((stat, idx) => {
            const Icon = stat.icon;
            return (
              <div
                key={idx}
                className={`flex items-center justify-between p-2 rounded-lg border transition-all ${
                  stat.isSuccess
                    ? 'bg-emerald-950/20 border-emerald-900/50'
                    : stat.isDrop
                    ? 'bg-red-950/10 border-red-900/20 text-slate-300'
                    : 'bg-slate-900/30 border-slate-800/60 text-slate-300'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Icon className={`w-3.5 h-3.5 ${stat.color}`} />
                  <span>{stat.label}</span>
                </div>
                <span className={`font-bold ${stat.isSuccess ? 'text-emerald-400 text-sm' : stat.isDrop ? 'text-red-400' : 'text-slate-200'}`}>
                  {stat.isDrop ? `-${stat.value}` : stat.value}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
