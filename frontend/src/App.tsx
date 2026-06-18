import { useState, useEffect } from 'react';
import { api } from './api';
import type { 
  Shop, 
  Department, 
  SummaryResponse, 
  GapRow, 
  GapKPIs, 
  ABCClass 
} from './types';
import { KPISection } from './components/KPISection';
import { FilterPanel } from './components/FilterPanel';
import { GapsTable } from './components/GapsTable';
import { CleaningSummary } from './components/CleaningSummary';
import { FileUploader } from './components/FileUploader';
import { 
  LayoutDashboard, 
  Database, 
  Upload, 
  AlertCircle, 
  RefreshCw, 
  Server,
  BarChart4
} from 'lucide-react';

function App() {
  // Navigation
  const [activeTab, setActiveTab] = useState<'dashboard' | 'cleaning' | 'upload'>('dashboard');

  // API Lists
  const [shops, setShops] = useState<Shop[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);

  // Analysis State
  const [gaps, setGaps] = useState<GapRow[]>([]);
  const [kpis, setKpis] = useState<GapKPIs | null>(null);
  const [hasRunAnalysis, setHasRunAnalysis] = useState<boolean>(false);

  // Filter Values
  const [selectedShop, setSelectedShop] = useState<number | null>(null);
  const [selectedDepartment, setSelectedDepartment] = useState<string | null>(null);
  const [selectedAbcClasses, setSelectedAbcClasses] = useState<ABCClass[]>(['A', 'B']);
  const [minShopsSelling, setMinShopsSelling] = useState<number>(3);
  const [gapThreshold, setGapThreshold] = useState<number>(0.20);

  // Loading & Connection Diagnostics
  const [isBackendConnected, setIsBackendConnected] = useState<boolean | null>(null);
  const [isCheckingHealth, setIsCheckingHealth] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState<boolean>(false);
  const [isLoadingGaps, setIsLoadingGaps] = useState<boolean>(false);
  const [isLoadingUpload, setIsLoadingUpload] = useState<boolean>(false);

  // Check backend health and load lookup dimensions
  const checkHealthAndLoadData = async () => {
    setIsCheckingHealth(true);
    setHealthError(null);
    try {
      const health = await api.getHealth();
      setIsBackendConnected(health.ready);
      
      if (health.ready) {
        setIsLoadingMetadata(true);
        // Fetch dimensions concurrently
        const [shopsList, deptsList, sumData] = await Promise.all([
          api.getShops(),
          api.getDepartments(),
          api.getSummary()
        ]);
        
        setShops(shopsList);
        setDepartments(deptsList);
        setSummary(sumData);
        
        // Auto-select first shop if none selected
        if (shopsList.length > 0 && !selectedShop) {
          // Shop 184 is a great default mentioned in spec, otherwise first shop code
          const defaultShop = shopsList.some(s => s.code === 184) 
            ? 184 
            : shopsList[0].code;
          setSelectedShop(defaultShop);
        }
      } else {
        if (health.status === 'loading') {
          setHealthError('The backend server is currently loading the Excel dataset (takes ~25-30s)...');
          // Retry health check in 5 seconds
          setTimeout(checkHealthAndLoadData, 5000);
        } else {
          setHealthError(health.load_error || 'Dataset not loaded on server.');
        }
      }
    } catch (err: any) {
      setIsBackendConnected(false);
      setHealthError(err.message || 'Could not connect to the API server.');
    } finally {
      setIsCheckingHealth(false);
      setIsLoadingMetadata(false);
    }
  };

  useEffect(() => {
    checkHealthAndLoadData();
  }, []);

  // Run Gap Analysis
  const handleRunAnalysis = async () => {
    if (!selectedShop) return;
    
    setIsLoadingGaps(true);
    try {
      const res = await api.getGaps({
        shop: selectedShop,
        department: selectedDepartment,
        abcClasses: selectedAbcClasses,
        minShopsSelling,
        gapThreshold
      });
      setGaps(res.rows);
      setKpis(res.kpis);
      setHasRunAnalysis(true);
    } catch (err: any) {
      console.error('Gap analysis query failed:', err);
      alert(`Gap analysis failed: ${err.message}`);
    } finally {
      setIsLoadingGaps(false);
    }
  };

  // Reset Filters
  const handleResetFilters = () => {
    if (shops.length > 0) {
      const defaultShop = shops.some(s => s.code === 184) ? 184 : shops[0].code;
      setSelectedShop(defaultShop);
    }
    setSelectedDepartment(null);
    setSelectedAbcClasses(['A', 'B']);
    setMinShopsSelling(3);
    setGapThreshold(0.20);
  };

  // Callback on successful spreadsheet upload
  const handleUploadSuccess = async () => {
    setActiveTab('dashboard');
    // Refresh dimensions since database changed
    await checkHealthAndLoadData();
    // Run analysis if a shop is selected
    if (selectedShop) {
      handleRunAnalysis();
    }
  };

  // Export URLs
  const excelExportUrl = selectedShop 
    ? api.getExcelExportUrl({
        shop: selectedShop,
        department: selectedDepartment,
        abcClasses: selectedAbcClasses,
        minShopsSelling,
        gapThreshold
      })
    : null;

  const pdfExportUrl = selectedShop 
    ? api.getPdfExportUrl({
        shop: selectedShop,
        department: selectedDepartment,
        abcClasses: selectedAbcClasses,
        minShopsSelling,
        gapThreshold
      })
    : null;

  // Render Loading / Error States
  if (isCheckingHealth && isBackendConnected === null) {
    return (
      <div className="min-h-screen bg-[#070b13] flex flex-col items-center justify-center p-6 text-center">
        <RefreshCw className="w-12 h-12 text-blue-500 animate-spin mb-4" />
        <h1 className="text-xl font-bold font-outfit text-slate-100">Connecting to API Server</h1>
        <p className="text-sm text-slate-400 mt-2">Checking backend service health status...</p>
      </div>
    );
  }

  if (isBackendConnected === false) {
    return (
      <div className="min-h-screen bg-[#070b13] flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-500 mb-6">
          <AlertCircle className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-bold font-outfit text-slate-100">API Connection Offline</h1>
        <p className="text-sm text-slate-400 mt-2 max-w-md">
          {healthError || 'Could not establish connection to the FastAPI server at http://localhost:8000.'}
        </p>
        
        <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 mt-6 text-left max-w-lg text-xs leading-relaxed font-mono">
          <p className="text-slate-400 mb-2"># Check if the FastAPI backend is running:</p>
          <p className="text-blue-400 font-semibold mb-3">python -m uvicorn backend.app.main:app --reload</p>
          <p className="text-slate-400"># The startup ETL takes 25-30s. If it is already starting, please wait and try again.</p>
        </div>

        <button
          onClick={checkHealthAndLoadData}
          className="mt-6 flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg text-sm transition-colors cursor-pointer"
        >
          <RefreshCw className="w-4 h-4" />
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#070b13] text-slate-100 font-sans pb-12">
      {/* Top Navbar */}
      <header className="border-b border-slate-900 bg-[#090d16]/85 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-600/10 border border-blue-500/30 flex items-center justify-center text-blue-500 shadow-md">
              <BarChart4 className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold font-outfit text-slate-100 leading-tight">Talal Group Retail</h1>
              <span className="text-[10px] text-slate-400 tracking-wider uppercase font-semibold">Missing Winners System</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              API Connected
            </span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-6">
        
        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-900 mb-6 pb-px">
          <button
            onClick={() => setActiveTab('dashboard')}
            className={`flex items-center gap-2 px-5 py-2.5 border-b-2 text-xs font-bold uppercase tracking-wider transition-all duration-200 cursor-pointer ${
              activeTab === 'dashboard'
                ? 'border-blue-500 text-blue-400 bg-blue-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            Assortment Analysis
          </button>
          
          <button
            onClick={() => setActiveTab('cleaning')}
            className={`flex items-center gap-2 px-5 py-2.5 border-b-2 text-xs font-bold uppercase tracking-wider transition-all duration-200 cursor-pointer ${
              activeTab === 'cleaning'
                ? 'border-blue-500 text-blue-400 bg-blue-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
            }`}
          >
            <Database className="w-4 h-4" />
            Data Cleaning Report
          </button>

          <button
            onClick={() => setActiveTab('upload')}
            className={`flex items-center gap-2 px-5 py-2.5 border-b-2 text-xs font-bold uppercase tracking-wider transition-all duration-200 cursor-pointer ${
              activeTab === 'upload'
                ? 'border-blue-500 text-blue-400 bg-blue-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/40'
            }`}
          >
            <Upload className="w-4 h-4" />
            Upload New Dataset
          </button>
        </div>

        {/* Tab Contents */}
        <div className="space-y-6">
          {activeTab === 'dashboard' && (
            <>
              {/* Filters */}
              <FilterPanel
                shops={shops}
                departments={departments}
                selectedShop={selectedShop}
                selectedDepartment={selectedDepartment}
                selectedAbcClasses={selectedAbcClasses}
                minShopsSelling={minShopsSelling}
                gapThreshold={gapThreshold}
                isLoading={isLoadingGaps}
                onChangeShop={setSelectedShop}
                onChangeDepartment={setSelectedDepartment}
                onChangeAbcClasses={setSelectedAbcClasses}
                onChangeMinShopsSelling={setMinShopsSelling}
                onChangeGapThreshold={setGapThreshold}
                onApplyFilters={handleRunAnalysis}
                onResetFilters={handleResetFilters}
                excelExportUrl={excelExportUrl}
                pdfExportUrl={pdfExportUrl}
              />

              {/* KPIs Section */}
              {hasRunAnalysis && <KPISection kpis={kpis} isLoading={isLoadingGaps} />}

              {/* Gaps Table View */}
              {hasRunAnalysis ? (
                <GapsTable rows={gaps} isLoading={isLoadingGaps} />
              ) : (
                <div className="flex flex-col items-center justify-center p-16 border border-slate-800 rounded-xl bg-[#0f172a]/30 text-center animate-fade-in">
                  <Server className="w-12 h-12 text-slate-600 mb-4" />
                  <h3 className="text-md font-semibold text-slate-300">Ready to Analyze</h3>
                  <p className="text-xs text-slate-500 max-w-sm mt-1">
                    Select a Shop Code and configure your thresholds above, then click <strong>Run Gap Analysis</strong> to scan assortment metrics.
                  </p>
                </div>
              )}
            </>
          )}

          {activeTab === 'cleaning' && (
            <CleaningSummary summary={summary} isLoading={isLoadingMetadata} />
          )}

          {activeTab === 'upload' && (
            <div className="max-w-2xl mx-auto py-4">
              <FileUploader
                onUploadSuccess={handleUploadSuccess}
                isLoading={isLoadingUpload}
                setIsLoading={setIsLoadingUpload}
              />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
