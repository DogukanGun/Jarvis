// API Client for Jarvis Backend Communication
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

// Types matching backend data structures
export interface SignupData {
  username: string;
  email: string;
  password: string;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface WalletAuthData {
  wallet_address: string;
  signature: string;
  message: string;
  full_name?: string;
  email?: string;
  password?: string;
  btc_tx_id?: string;
}

export interface AuthResponse {
  user_id: string;
  username: string;
  email: string;
  container_id: string;
  token: string;
  created_at?: string;
  last_active?: string;
}

export interface Container {
  container_id: string;
  user_id: string;
  port: number;
  status: string;
  created: string;
  last_used: string;
  is_running: boolean;
}

export interface ChatMessage {
  message: string;
}

export interface ChatResponse {
  response: string;
  processed_at: string;
  user_id: string;
  container_id: string;
}

export interface Invoice {
  id: string;
  user_id: string;
  month: number;
  year: number;
  amount: number;
  transaction_hash: string;
  is_paid: boolean;
  created_at: string;
  last_active: string;
  paid_at?: string;
}

// Helper function to get auth token
const getAuthToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth-token');
};

// Helper function to handle API responses
const handleResponse = async <T>(response: Response): Promise<T> => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'An error occurred' }));
    throw new Error(error.message || `HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
};

// API Client
export const apiClient = {
  // Authentication endpoints
  auth: {
    signup: async (data: SignupData): Promise<AuthResponse> => {
      const response = await fetch(`${API_BASE_URL}/api/v1/users/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      return handleResponse<AuthResponse>(response);
    },

    login: async (data: LoginData): Promise<AuthResponse> => {
      const response = await fetch(`${API_BASE_URL}/api/v1/users/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      return handleResponse<AuthResponse>(response);
    },

    walletAuth: async (data: WalletAuthData): Promise<AuthResponse> => {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/wallet`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      return handleResponse<AuthResponse>(response);
    },

    logout: async (): Promise<void> => {
      try {
        const token = getAuthToken();
        if (token) {
          // Call backend logout endpoint
          await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
        }
      } catch (error) {
        console.error('Backend logout failed:', error);
        // Continue with local cleanup even if backend fails
      } finally {
        // Always clean up local storage
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth-token');
          localStorage.removeItem('user');
          localStorage.removeItem('container-info');
        }
      }
    },
  },

  // Container/Agent endpoints
  containers: {
    // Get container status (uses user's container from backend)
    getStatus: async (): Promise<Container> => {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/containers/status`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      return handleResponse<Container>(response);
    },

    start: async (): Promise<{ message: string }> => {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/containers/start`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      return handleResponse<{ message: string }>(response);
    },

    stop: async (): Promise<{ message: string }> => {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/containers/stop`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      return handleResponse<{ message: string }>(response);
    },

    // Send message to agent
    sendMessage: async (message: ChatMessage): Promise<ChatResponse> => {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/containers/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(message),
      });
      return handleResponse<ChatResponse>(response);
    },
  },

  // User endpoints
  users: {
    getProfile: async (): Promise<AuthResponse> => {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/users/profile`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      return handleResponse<AuthResponse>(response);
    },

    updateProfile: async (data: Partial<SignupData>): Promise<AuthResponse> => {
      const token = getAuthToken();
      const user = getCurrentUser();
      if (!user) throw new Error('Not authenticated');
      
      const response = await fetch(`${API_BASE_URL}/api/v1/users/${user.user_id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      });
      return handleResponse<AuthResponse>(response);
    },
  },

  // Invoice endpoints
  invoices: {
    getAll: async (): Promise<Invoice[]> => {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/invoices`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      return handleResponse<Invoice[]>(response);
    },

    getUnpaid: async (): Promise<Invoice[]> => {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/invoices/unpaid`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      return handleResponse<Invoice[]>(response);
    },

    checkPayment: async (invoiceId: string): Promise<Invoice> => {
      const token = getAuthToken();
      const response = await fetch(`${API_BASE_URL}/api/v1/invoices/${invoiceId}/check-payment`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      return handleResponse<Invoice>(response);
    },
  },
};

// Helper to check if user is authenticated
export const isAuthenticated = (): boolean => {
  if (typeof window === 'undefined') return false;
  return !!getAuthToken();
};

// Helper to get current user from localStorage
export const getCurrentUser = (): AuthResponse | null => {
  if (typeof window === 'undefined') return null;
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
};

// Helper to get container info from localStorage
export const getContainerInfo = (): Container | null => {
  if (typeof window === 'undefined') return null;
  const containerStr = localStorage.getItem('container-info');
  return containerStr ? JSON.parse(containerStr) : null;
};

// Helper to save container info
export const saveContainerInfo = (container: Container): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('container-info', JSON.stringify(container));
  }
};
