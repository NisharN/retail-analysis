import type { 
  HealthResponse, 
  Shop, 
  Department, 
  SummaryResponse, 
  GapResponse, 
  UploadResponse 
} from './types';

// Use environment variable or default to localhost:8000
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Handle API responses and throw informative errors
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = 'API error occurred';
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail?.message || errorJson.detail || JSON.stringify(errorJson);
    } catch {
      errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorDetail);
  }
  return response.json() as Promise<T>;
}

export const api = {
  /**
   * Check system health and dataset status
   */
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE_URL}/health`);
    return handleResponse<HealthResponse>(res);
  },

  /**
   * Retrieve list of active shops (cleaned dataset only)
   */
  async getShops(): Promise<Shop[]> {
    const res = await fetch(`${API_BASE_URL}/api/shops`);
    return handleResponse<Shop[]>(res);
  },

  /**
   * Retrieve list of departments
   */
  async getDepartments(): Promise<Department[]> {
    const res = await fetch(`${API_BASE_URL}/api/departments`);
    return handleResponse<Department[]>(res);
  },

  /**
   * Retrieve cleaning statistics and catalog-wide data summaries
   */
  async getSummary(): Promise<SummaryResponse> {
    const res = await fetch(`${API_BASE_URL}/api/summary`);
    return handleResponse<SummaryResponse>(res);
  },

  /**
   * Run the assortment gap analysis with specific filter constraints
   */
  async getGaps(params: {
    shop: number;
    department?: string | null;
    abcClasses?: string[];
    minShopsSelling?: number;
    gapThreshold?: number;
  }): Promise<GapResponse> {
    const query = new URLSearchParams();
    query.append('shop', params.shop.toString());
    
    if (params.department) {
      query.append('department', params.department);
    }
    if (params.abcClasses && params.abcClasses.length > 0) {
      query.append('abc_classes', params.abcClasses.join(','));
    }
    if (params.minShopsSelling !== undefined) {
      query.append('min_shops_selling', params.minShopsSelling.toString());
    }
    if (params.gapThreshold !== undefined) {
      query.append('gap_threshold', params.gapThreshold.toString());
    }

    const res = await fetch(`${API_BASE_URL}/api/gaps?${query.toString()}`);
    return handleResponse<GapResponse>(res);
  },

  /**
   * Upload a new dataset (must be .xlsx format).
   * Note: This request takes 25-30 seconds because the pipeline performs full cleaning and indexing on upload.
   */
  async uploadDataset(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<UploadResponse>(res);
  },

  /**
   * Generate links to the Excel spreadsheet export endpoint
   */
  getExcelExportUrl(params: {
    shop: number;
    department?: string | null;
    abcClasses?: string[];
    minShopsSelling?: number;
    gapThreshold?: number;
  }): string {
    const query = new URLSearchParams();
    query.append('shop', params.shop.toString());
    
    if (params.department) {
      query.append('department', params.department);
    }
    if (params.abcClasses && params.abcClasses.length > 0) {
      query.append('abc_classes', params.abcClasses.join(','));
    }
    if (params.minShopsSelling !== undefined) {
      query.append('min_shops_selling', params.minShopsSelling.toString());
    }
    if (params.gapThreshold !== undefined) {
      query.append('gap_threshold', params.gapThreshold.toString());
    }

    return `${API_BASE_URL}/api/gaps/export.xlsx?${query.toString()}`;
  },

  /**
   * Generate links to the PDF summary report export endpoint
   */
  getPdfExportUrl(params: {
    shop: number;
    department?: string | null;
    abcClasses?: string[];
    minShopsSelling?: number;
    gapThreshold?: number;
  }): string {
    const query = new URLSearchParams();
    query.append('shop', params.shop.toString());
    
    if (params.department) {
      query.append('department', params.department);
    }
    if (params.abcClasses && params.abcClasses.length > 0) {
      query.append('abc_classes', params.abcClasses.join(','));
    }
    if (params.minShopsSelling !== undefined) {
      query.append('min_shops_selling', params.minShopsSelling.toString());
    }
    if (params.gapThreshold !== undefined) {
      query.append('gap_threshold', params.gapThreshold.toString());
    }

    return `${API_BASE_URL}/api/gaps/export.pdf?${query.toString()}`;
  }
};
