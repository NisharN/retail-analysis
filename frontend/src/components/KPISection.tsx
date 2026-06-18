import React from 'react';
import type { GapKPIs } from '../types';
import { AlertCircle, AlertTriangle, DollarSign, Package } from 'lucide-react';

interface KPISectionProps {
  kpis: GapKPIs | null;
  isLoading: boolean;
}

export const KPISection: React.FC<KPISectionProps> = ({ kpis, isLoading }) => {
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(val).replace('$', '¤ '); // Use a generic currency symbol as per CLAUDE.md guidelines
  };

  const cards = [
    {
      title: 'Potential Revenue Opportunity',
      value: kpis ? formatCurrency(kpis.potential_revenue) : '¤ 0',
      description: 'Lost revenue from unstocked/underperforming winners',
      icon: DollarSign,
      color: 'from-emerald-500/20 to-teal-500/20 border-emerald-500/30 text-emerald-400',
      iconColor: 'bg-emerald-500/10 text-emerald-400',
    },
    {
      title: 'Total Assortment Gaps',
      value: kpis ? kpis.total_gaps.toLocaleString() : '0',
      description: `Class A: ${kpis?.class_a_gaps || 0} | Class B: ${kpis?.class_b_gaps || 0}`,
      icon: Package,
      color: 'from-blue-500/20 to-indigo-500/20 border-blue-500/30 text-blue-400',
      iconColor: 'bg-blue-500/10 text-blue-400',
    },
    {
      title: 'Missing Winners',
      value: kpis ? kpis.missing_winners.toLocaleString() : '0',
      description: 'Top-selling products never stocked in store',
      icon: AlertCircle,
      color: 'from-red-500/20 to-orange-500/20 border-red-500/30 text-red-400',
      iconColor: 'bg-red-500/10 text-red-400',
    },
    {
      title: 'Underperforming',
      value: kpis ? kpis.underperforming.toLocaleString() : '0',
      description: 'Products stocked but selling under target',
      icon: AlertTriangle,
      color: 'from-amber-500/20 to-yellow-500/20 border-amber-500/30 text-amber-400',
      iconColor: 'bg-amber-500/10 text-amber-400',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`relative overflow-hidden rounded-xl border bg-gradient-to-br ${card.color} p-5 shadow-lg backdrop-blur-md transition-all duration-300 hover:scale-[1.02] hover:shadow-xl`}
          >
            {isLoading && (
              <div className="absolute inset-0 bg-[#090d16]/30 backdrop-blur-xs flex items-center justify-center">
                <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
              </div>
            )}
            <div className="flex justify-between items-start">
              <div>
                <p className="text-xs font-semibold tracking-wider text-gray-400 uppercase">
                  {card.title}
                </p>
                <h3 className="mt-2 text-3xl font-bold font-outfit tracking-tight">
                  {card.value}
                </h3>
                <p className="mt-2 text-xs text-gray-300 font-medium">
                  {card.description}
                </p>
              </div>
              <div className={`rounded-lg p-2 ${card.iconColor} p-2.5`}>
                <Icon className="w-5 h-5" />
              </div>
            </div>
            
            {/* Elegant glassmorphism lighting decoration */}
            <div className="absolute -right-6 -bottom-6 w-24 h-24 rounded-full bg-white/3 blur-xl pointer-events-none"></div>
          </div>
        );
      })}
    </div>
  );
};
