import React, { useState } from 'react';
import type { GapRow } from '../types';
import { ChevronDown, ChevronUp, Search, Info } from 'lucide-react';

interface GapsTableProps {
  rows: GapRow[];
  isLoading: boolean;
}

type SortField = 'ArticleCode' | 'DepartmentName' | 'ABCClass' | 'NumShopsSelling' | 'ShopSaleValue' | 'ChainAvgSaleValue' | 'GapScore' | 'PotentialLostRevenue' | 'Status';
type SortOrder = 'asc' | 'desc';

export const GapsTable: React.FC<GapsTableProps> = ({ rows, isLoading }) => {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortField, setSortField] = useState<SortField>('PotentialLostRevenue');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(25);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc'); // Default to descending for numbers
    }
    setCurrentPage(1);
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(val).replace('$', '¤ ');
  };

  const formatPercent = (val: number) => {
    return `${Math.round(val * 100)}%`;
  };

  // Filter rows
  const filteredRows = rows.filter((r) => 
    r.ArticleCode.toString().includes(searchTerm) ||
    r.DepartmentName.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sort rows
  const sortedRows = [...filteredRows].sort((a, b) => {
    let aVal = a[sortField];
    let bVal = b[sortField];

    if (typeof aVal === 'string') {
      return sortOrder === 'asc' 
        ? (aVal as string).localeCompare(bVal as string)
        : (bVal as string).localeCompare(aVal as string);
    } else {
      // numeric comparison
      return sortOrder === 'asc'
        ? (aVal as number) - (bVal as number)
        : (bVal as number) - (aVal as number);
    }
  });

  // Paginate rows
  const totalPages = Math.ceil(sortedRows.length / pageSize) || 1;
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedRows = sortedRows.slice(startIndex, startIndex + pageSize);

  const SortIndicator = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortOrder === 'asc' 
      ? <ChevronUp className="w-4 h-4 ml-1 inline text-blue-400" />
      : <ChevronDown className="w-4 h-4 ml-1 inline text-blue-400" />;
  };

  return (
    <div className="bg-[#0f172a]/80 backdrop-blur-md border border-slate-800 rounded-xl p-5 shadow-xl animate-fade-in mt-6">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-800 mb-5">
        <div className="flex items-center gap-3">
          <h2 className="text-md font-semibold text-slate-200">Gaps &amp; Opportunities</h2>
          <span className="bg-slate-800 text-slate-400 text-xs font-semibold px-2 py-0.5 rounded">
            {filteredRows.length} {filteredRows.length === 1 ? 'record' : 'records'}
          </span>
        </div>
        
        <div className="flex flex-wrap items-center gap-3">
          {/* Search box */}
          <div className="relative w-full sm:w-60">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <Search className="w-4 h-4" />
            </span>
            <input
              type="text"
              placeholder="Search Article Code / Dept..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full bg-[#1e293b]/70 border border-slate-700 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Page size select */}
          <select
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="bg-[#1e293b]/70 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-300 outline-hidden cursor-pointer"
          >
            <option value={10}>10 per page</option>
            <option value={25}>25 per page</option>
            <option value={50}>50 per page</option>
            <option value={100}>100 per page</option>
          </select>
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-lg border border-slate-850 bg-slate-900/30">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-950/60 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
              <th onClick={() => handleSort('ArticleCode')} className="px-4 py-3 cursor-pointer hover:bg-slate-800 transition-colors select-none w-28">
                Article Code <SortIndicator field="ArticleCode" />
              </th>
              <th onClick={() => handleSort('DepartmentName')} className="px-4 py-3 cursor-pointer hover:bg-slate-800 transition-colors select-none">
                Department <SortIndicator field="DepartmentName" />
              </th>
              <th onClick={() => handleSort('ABCClass')} className="px-4 py-3 cursor-pointer text-center hover:bg-slate-800 transition-colors select-none w-24">
                ABC Class <SortIndicator field="ABCClass" />
              </th>
              <th onClick={() => handleSort('NumShopsSelling')} className="px-4 py-3 cursor-pointer text-center hover:bg-slate-800 transition-colors select-none w-32" title="How many other shops stock this product chain-wide">
                Shops Selling <SortIndicator field="NumShopsSelling" />
              </th>
              <th onClick={() => handleSort('ShopSaleValue')} className="px-4 py-3 cursor-pointer text-right hover:bg-slate-800 transition-colors select-none w-28">
                Shop Sales <SortIndicator field="ShopSaleValue" />
              </th>
              <th onClick={() => handleSort('ChainAvgSaleValue')} className="px-4 py-3 cursor-pointer text-right hover:bg-slate-800 transition-colors select-none w-32">
                Chain Avg Sales <SortIndicator field="ChainAvgSaleValue" />
              </th>
              <th onClick={() => handleSort('GapScore')} className="px-4 py-3 cursor-pointer text-center hover:bg-slate-800 transition-colors select-none w-28" title="Calculation: (ChainAvg - ShopSales) / ChainAvg">
                Gap Score <SortIndicator field="GapScore" />
              </th>
              <th onClick={() => handleSort('PotentialLostRevenue')} className="px-4 py-3 cursor-pointer text-right hover:bg-slate-800 transition-colors select-none w-36">
                Lost Revenue <SortIndicator field="PotentialLostRevenue" />
              </th>
              <th onClick={() => handleSort('Status')} className="px-4 py-3 cursor-pointer text-center hover:bg-slate-800 transition-colors select-none w-36">
                Status <SortIndicator field="Status" />
              </th>
              <th className="px-4 py-3 text-center w-28">
                Distribution
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {isLoading ? (
              <tr>
                <td colSpan={10} className="px-4 py-16 text-center text-slate-500">
                  <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                  Recalculating assortment gap analysis...
                </td>
              </tr>
            ) : paginatedRows.length === 0 ? (
              <tr>
                <td colSpan={10} className="px-4 py-16 text-center text-slate-500">
                  No gaps found matching current filter options.
                </td>
              </tr>
            ) : (
              paginatedRows.map((row) => (
                <tr 
                  key={row.ArticleCode} 
                  className="hover:bg-slate-800/40 transition-colors"
                >
                  <td className="px-4 py-3 font-semibold text-slate-300 font-mono">
                    {row.ArticleCode}
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {row.DepartmentName}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      row.ABCClass === 'A' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                      row.ABCClass === 'B' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                      'bg-slate-700/10 text-slate-400 border border-slate-700/20'
                    }`}>
                      Class {row.ABCClass}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-slate-300 font-medium">
                    {row.NumShopsSelling} / 74
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-slate-400">
                    {formatCurrency(row.ShopSaleValue)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-slate-400">
                    {formatCurrency(row.ChainAvgSaleValue)}
                  </td>
                  <td className="px-4 py-3 text-center font-semibold text-slate-300">
                    {formatPercent(row.GapScore)}
                  </td>
                  <td className="px-4 py-3 text-right font-bold font-mono text-emerald-400">
                    {formatCurrency(row.PotentialLostRevenue)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-semibold tracking-wide ${
                      row.Status === 'Missing Winner' 
                        ? 'bg-red-500/15 text-red-400 border border-red-500/20' 
                        : 'bg-amber-500/15 text-amber-400 border border-amber-500/20'
                    }`}>
                      {row.Status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    {row.NeverStocked ? (
                      <span 
                        className="inline-flex items-center gap-1 text-[10px] bg-red-950/20 border border-red-900/30 text-red-400 px-1.5 py-0.5 rounded-sm"
                        title="Never Stocked: Shop has no sales rows for this article"
                      >
                        <Info className="w-3 h-3" />
                        Never Stocked
                      </span>
                    ) : (
                      <span 
                        className="inline-flex items-center gap-1 text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded-sm"
                        title="Stocked: Shop contains rows but sales are underperforming"
                      >
                        Stocked Gap
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {sortedRows.length > 0 && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mt-4 pt-4 border-t border-slate-800">
          <span className="text-xs text-slate-500 text-center sm:text-left">
            Showing <strong className="text-slate-300">{startIndex + 1}</strong> to{' '}
            <strong className="text-slate-300">
              {Math.min(startIndex + pageSize, sortedRows.length)}
            </strong>{' '}
            of <strong className="text-slate-300">{sortedRows.length}</strong> items
          </span>

          <div className="flex items-center justify-center gap-1.5">
            <button
              onClick={() => setCurrentPage(1)}
              disabled={currentPage === 1 || isLoading}
              className="px-2.5 py-1 bg-slate-800 text-slate-300 rounded border border-slate-700 text-xs font-semibold hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              First
            </button>
            <button
              onClick={() => setCurrentPage((c) => Math.max(c - 1, 1))}
              disabled={currentPage === 1 || isLoading}
              className="px-2.5 py-1 bg-slate-800 text-slate-300 rounded border border-slate-700 text-xs font-semibold hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              Prev
            </button>
            
            <span className="text-xs text-slate-400 px-3">
              Page <strong className="text-slate-200">{currentPage}</strong> of{' '}
              <strong className="text-slate-200">{totalPages}</strong>
            </span>

            <button
              onClick={() => setCurrentPage((c) => Math.min(c + 1, totalPages))}
              disabled={currentPage === totalPages || isLoading}
              className="px-2.5 py-1 bg-slate-800 text-slate-300 rounded border border-slate-700 text-xs font-semibold hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              Next
            </button>
            <button
              onClick={() => setCurrentPage(totalPages)}
              disabled={currentPage === totalPages || isLoading}
              className="px-2.5 py-1 bg-slate-800 text-slate-300 rounded border border-slate-700 text-xs font-semibold hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              Last
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
