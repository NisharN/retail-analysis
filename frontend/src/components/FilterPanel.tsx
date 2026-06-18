import React from 'react';
import type { Shop, Department, ABCClass } from '../types';
import { Filter, RotateCcw, FileSpreadsheet, FileText } from 'lucide-react';

interface FilterPanelProps {
  shops: Shop[];
  departments: Department[];
  selectedShop: number | null;
  selectedDepartment: string | null;
  selectedAbcClasses: ABCClass[];
  minShopsSelling: number;
  gapThreshold: number;
  isLoading: boolean;
  
  onChangeShop: (shop: number) => void;
  onChangeDepartment: (dept: string | null) => void;
  onChangeAbcClasses: (classes: ABCClass[]) => void;
  onChangeMinShopsSelling: (min: number) => void;
  onChangeGapThreshold: (threshold: number) => void;
  onApplyFilters: () => void;
  onResetFilters: () => void;
  excelExportUrl: string | null;
  pdfExportUrl: string | null;
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  shops,
  departments,
  selectedShop,
  selectedDepartment,
  selectedAbcClasses,
  minShopsSelling,
  gapThreshold,
  isLoading,
  onChangeShop,
  onChangeDepartment,
  onChangeAbcClasses,
  onChangeMinShopsSelling,
  onChangeGapThreshold,
  onApplyFilters,
  onResetFilters,
  excelExportUrl,
  pdfExportUrl,
}) => {
  const toggleAbcClass = (abc: ABCClass) => {
    if (selectedAbcClasses.includes(abc)) {
      // Keep at least one checked
      if (selectedAbcClasses.length > 1) {
        onChangeAbcClasses(selectedAbcClasses.filter((c) => c !== abc));
      }
    } else {
      onChangeAbcClasses([...selectedAbcClasses, abc]);
    }
  };

  return (
    <div className="bg-[#0f172a]/80 backdrop-blur-md border border-slate-800 rounded-xl p-5 shadow-xl animate-fade-in">
      <div className="flex items-center gap-2 pb-4 border-b border-slate-800 mb-5">
        <Filter className="w-4 h-4 text-blue-400" />
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">Analysis Configuration</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {/* Shop Selector */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-400" htmlFor="shop-select">
            Select Shop *
          </label>
          <select
            id="shop-select"
            value={selectedShop || ''}
            onChange={(e) => onChangeShop(Number(e.target.value))}
            className="w-full bg-[#1e293b]/70 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500 cursor-pointer"
          >
            <option value="" disabled>-- Select a Shop --</option>
            {shops.map((s) => (
              <option key={s.code} value={s.code}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {/* Department Selector */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-400" htmlFor="dept-select">
            Department
          </label>
          <select
            id="dept-select"
            value={selectedDepartment || ''}
            onChange={(e) => onChangeDepartment(e.target.value || null)}
            className="w-full bg-[#1e293b]/70 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 outline-hidden focus:border-blue-500 focus:ring-1 focus:ring-blue-500 cursor-pointer"
          >
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d.name} value={d.name}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        {/* ABC Class Checkboxes */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-slate-400">ABC Classes</label>
          <div className="flex items-center gap-4 py-2">
            {(['A', 'B', 'C'] as ABCClass[]).map((abc) => (
              <label key={abc} className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={selectedAbcClasses.includes(abc)}
                  onChange={() => toggleAbcClass(abc)}
                  className="rounded-sm border-slate-700 bg-slate-900 text-blue-500 focus:ring-blue-500 focus:ring-offset-slate-950 w-4 h-4 cursor-pointer"
                />
                <span className={`font-semibold px-2 py-0.5 rounded text-xs ${
                  abc === 'A' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                  abc === 'B' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                  'bg-slate-500/20 text-slate-400 border border-slate-500/30'
                }`}>
                  Class {abc}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Minimum Shops Selling */}
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between items-center">
            <label className="text-xs font-semibold text-slate-400" htmlFor="min-shops">
              Min Shops Selling
            </label>
            <span className="text-xs font-bold text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">
              ≥ {minShopsSelling}
            </span>
          </div>
          <input
            id="min-shops"
            type="range"
            min="1"
            max="74"
            value={minShopsSelling}
            onChange={(e) => onChangeMinShopsSelling(Number(e.target.value))}
            className="w-full accent-blue-500 py-2.5 cursor-pointer bg-transparent focus:outline-hidden"
          />
        </div>

        {/* Gap Threshold percentage */}
        <div className="flex flex-col gap-1.5">
          <div className="flex justify-between items-center">
            <label className="text-xs font-semibold text-slate-400" htmlFor="gap-threshold">
              Gap Limit Threshold
            </label>
            <span className="text-xs font-bold text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
              &lt; {Math.round(gapThreshold * 100)}%
            </span>
          </div>
          <input
            id="gap-threshold"
            type="range"
            min="5"
            max="100"
            step="5"
            value={gapThreshold * 100}
            onChange={(e) => onChangeGapThreshold(Number(e.target.value) / 100)}
            className="w-full accent-amber-500 py-2.5 cursor-pointer bg-transparent focus:outline-hidden"
          />
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4 mt-6 pt-4 border-t border-slate-800">
        {/* Reset & Apply */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={onResetFilters}
            disabled={isLoading}
            className="flex items-center justify-center gap-2 px-4 py-2 border border-slate-700 text-slate-300 rounded-lg text-sm font-medium hover:bg-slate-800 disabled:opacity-50 cursor-pointer transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          
          <button
            onClick={onApplyFilters}
            disabled={isLoading || !selectedShop}
            className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-colors shadow-lg shadow-blue-900/30"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              'Run Gap Analysis'
            )}
          </button>
        </div>

        {/* Exports */}
        {selectedShop && excelExportUrl && pdfExportUrl && !isLoading && (
          <div className="flex items-center gap-3 w-full sm:w-auto justify-end border-t border-slate-800/50 sm:border-t-0 pt-3 sm:pt-0">
            <span className="text-xs text-slate-500 hidden md:inline">Download Results:</span>
            
            <a
              href={excelExportUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3.5 py-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20 rounded-lg text-xs font-semibold cursor-pointer transition-all"
              title="Export Full analysis as Excel Worksheet"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              Excel Export
            </a>

            <a
              href={pdfExportUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3.5 py-2 bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 rounded-lg text-xs font-semibold cursor-pointer transition-all"
              title="Export Executive Summary report as PDF"
            >
              <FileText className="w-3.5 h-3.5" />
              PDF Export
            </a>
          </div>
        )}
      </div>
    </div>
  );
};
