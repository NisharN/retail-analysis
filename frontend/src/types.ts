export type ABCClass = 'A' | 'B' | 'C';

export type GapStatus = 'Missing Winner' | 'Underperforming';

export type HealthStatus = 'ok' | 'loading' | 'error';

export interface CleaningReport {
  rows_before: number;
  duplicates_removed: number;
  returns_flagged: number;
  zero_sales_flagged: number;
  anomalies_flagged: number;
  dummy_rows_removed: number;
  group_income_rows_removed: number;
  rows_after: number;
  unique_articles: number;
  unique_shops: number;
  unique_departments: number;
}

export interface ABCDistribution {
  A: number;
  B: number;
  C: number;
  total: number;
}

export interface SummaryResponse {
  cleaning: CleaningReport;
  abc_distribution: ABCDistribution;
  total_products: number;
  total_revenue: number;
}

export interface Shop {
  code: number;
  label: string;
}

export interface Department {
  name: string;
}

export interface GapFiltersIn {
  shop: number;
  department: string | null;
  abc_classes: ABCClass[];
  min_shops_selling: number;
  gap_threshold: number;
}

export interface GapRow {
  ArticleCode: number;
  DepartmentName: string;
  ABCClass: ABCClass;
  NumShopsSelling: number;
  ShopSaleValue: number;
  ChainAvgSaleValue: number;
  GapScore: number;
  PotentialLostRevenue: number;
  Status: GapStatus;
  NeverStocked: boolean;
}

export interface GapKPIs {
  missing_winners: number;
  underperforming: number;
  potential_revenue: number;
  class_a_gaps: number;
  class_b_gaps: number;
  total_gaps: number;
}

export interface GapResponse {
  kpis: GapKPIs;
  rows: GapRow[];
  filters: GapFiltersIn;
  generated_in_ms: number;
}

export interface HealthResponse {
  ready: boolean;
  status: HealthStatus;
  dataset_loaded: boolean;
  load_error: string | null;
}

export interface UploadResponse {
  cleaning: CleaningReport;
  rows_replaced: boolean;
}
