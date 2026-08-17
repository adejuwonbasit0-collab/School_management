import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api').replace(/\/+$/, '');

const normalizeApiPath = (url?: string) => {
  if (!url || /^https?:\/\//i.test(url)) return url;

  const path = url.startsWith('/') ? url : `/${url}`;
  if (path === '/api') return '/v1';
  if (path.startsWith('/api/v')) return path.replace(/^\/api/, '');
  if (path.startsWith('/api/')) return `/v1${path.slice(4)}`;
  if (path === '/v1' || path.startsWith('/v1/')) return path;
  return `/v1${path}`;
};

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─── Request Interceptor ─────────────────────────────────────────────────────
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    config.url = normalizeApiPath(config.url);

    // Inject school ID from localStorage if available
    if (typeof window !== 'undefined') {
      const authData = localStorage.getItem('educore-auth');
      if (authData) {
        const { state } = JSON.parse(authData);
        if (state?.user?.schoolId) {
          config.headers['X-School-ID'] = state.user.schoolId;
        }
        if (state?.accessToken && !config.headers['Authorization']) {
          config.headers['Authorization'] = `Bearer ${state.accessToken}`;
        }
      }
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ─── Response Interceptor ─────────────────────────────────────────────────────
let isRefreshing = false;
let failedQueue: Array<{ resolve: Function; reject: Function }> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token)));
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers['Authorization'] = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const authData = localStorage.getItem('educore-auth');
        if (!authData) throw new Error('No auth data');

        const { state } = JSON.parse(authData);
        if (!state?.refreshToken) throw new Error('No refresh token');

        const response = await axios.post(`${API_BASE}/v1/auth/refresh`, {
          refreshToken: state.refreshToken,
        });

        const { tokens, user } = response.data.data;
        const newToken = tokens.accessToken;

        // Update stored tokens
        const updatedState = {
          ...state,
          accessToken: newToken,
          refreshToken: tokens.refreshToken,
          user,
        };
        localStorage.setItem('educore-auth', JSON.stringify({ state: updatedState }));
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;

        processQueue(null, newToken);
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as Error, null);
        localStorage.removeItem('educore-auth');
        window.location.href = '/auth/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  },
);

// ─── Typed API Helpers ────────────────────────────────────────────────────────
export const api = {
  get: <T>(url: string, params?: any) =>
    apiClient.get<{ data: T; success: boolean }>(url, { params }).then((r) => r.data.data),

  post: <T>(url: string, data?: any) =>
    apiClient.post<{ data: T; success: boolean }>(url, data).then((r) => r.data.data),

  put: <T>(url: string, data?: any) =>
    apiClient.put<{ data: T; success: boolean }>(url, data).then((r) => r.data.data),

  patch: <T>(url: string, data?: any) =>
    apiClient.patch<{ data: T; success: boolean }>(url, data).then((r) => r.data.data),

  delete: <T>(url: string) =>
    apiClient.delete<{ data: T; success: boolean }>(url).then((r) => r.data.data),

  upload: <T>(url: string, formData: FormData, onProgress?: (p: number) => void) =>
    apiClient
      .post<{ data: T }>(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
        },
      })
      .then((r) => r.data.data),
};

export default api;
