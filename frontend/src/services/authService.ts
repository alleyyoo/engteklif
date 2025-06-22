// src/services/authService.ts
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5050';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  name: string;
  surname: string;
  email: string;
  password: string;
  role?: string;
}

export interface AuthResponse {
  success: boolean;
  message: string;
  user?: {
    id: string;
    username: string;
    name: string;
    surname: string;
    email: string;
    role: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
  };
  tokens?: {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
  };
}

export interface User {
  id: string;
  username: string;
  name: string;
  surname: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

class AuthService {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('accessToken');
    return {
      'Authorization': token ? `Bearer ${token}` : '',
      'Content-Type': 'application/json',
    };
  }

  isAdmin(): boolean {
    const user = this.getCurrentUserFromStorage();
    return user?.role === 'admin';
  }
  
  isUser(): boolean {
    const user = this.getCurrentUserFromStorage();
    return user?.role === 'user';
  }
  
  hasRole(role: string): boolean {
    const user = this.getCurrentUserFromStorage();
    return user?.role === role;
  }

  async login(credentials: LoginRequest): Promise<AuthResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });
  
      const data: AuthResponse = await response.json();
  
      if (data.success && data.tokens) {
        // Token'ları localStorage'a kaydet
        localStorage.setItem('accessToken', data.tokens.access_token);
        localStorage.setItem('refreshToken', data.tokens.refresh_token);
        localStorage.setItem('tokenType', data.tokens.token_type);
        localStorage.setItem('expiresIn', data.tokens.expires_in.toString());
        
        // Kullanıcı bilgilerini kaydet
        if (data.user) {
          localStorage.setItem('user', JSON.stringify(data.user));
          console.log('✅ User logged in:', {
            username: data.user.username,
            role: data.user.role,
            id: data.user.id
          });
        }
      }
  
      return data;
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Bağlantı hatası'
      };
    }
  }
  
  // Logout'ta user bilgilerini de temizle
  async logout(): Promise<{ success: boolean; message?: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
      });
  
      const data = await response.json();
  
      // Her durumda localStorage'ı temizle
      this.clearLocalStorage();
      console.log('👋 User logged out');
  
      return { success: true, message: 'Başarıyla çıkış yapıldı' };
    } catch (error) {
      // Hata durumunda da localStorage'ı temizle
      this.clearLocalStorage();
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Çıkış yapılırken hata oluştu'
      };
    }
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      const data: AuthResponse = await response.json();

      if (data.success && data.tokens) {
        // Token'ları localStorage'a kaydet
        localStorage.setItem('accessToken', data.tokens.access_token);
        localStorage.setItem('refreshToken', data.tokens.refresh_token);
        localStorage.setItem('tokenType', data.tokens.token_type);
        localStorage.setItem('expiresIn', data.tokens.expires_in.toString());
        
        // Kullanıcı bilgilerini kaydet
        if (data.user) {
          localStorage.setItem('user', JSON.stringify(data.user));
        }
      }

      return data;
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Bağlantı hatası'
      };
    }
  }

  async getCurrentUser(): Promise<{ success: boolean; user?: User; message?: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
        method: 'GET',
        headers: this.getAuthHeaders(),
      });

      const data = await response.json();

      if (data.success) {
        // Kullanıcı bilgilerini güncelle
        localStorage.setItem('user', JSON.stringify(data.user));
        return { success: true, user: data.user };
      } else {
        return { success: false, message: data.message };
      }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Kullanıcı bilgileri alınamadı'
      };
    }
  }

  async refreshToken(): Promise<{ success: boolean; tokens?: any; message?: string }> {
    try {
      const refreshToken = localStorage.getItem('refreshToken');
      
      if (!refreshToken) {
        return { success: false, message: 'Refresh token bulunamadı' };
      }

      const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${refreshToken}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.success && data.tokens) {
        // Yeni token'ları kaydet
        localStorage.setItem('accessToken', data.tokens.access_token);
        localStorage.setItem('refreshToken', data.tokens.refresh_token);
        localStorage.setItem('tokenType', data.tokens.token_type);
        localStorage.setItem('expiresIn', data.tokens.expires_in.toString());
        
        return { success: true, tokens: data.tokens };
      } else {
        return { success: false, message: data.message };
      }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Token yenilenemedi'
      };
    }
  }

  async changePassword(oldPassword: string, newPassword: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/change-password`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
        }),
      });

      const data = await response.json();
      return data;
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Şifre değiştirilemedi'
      };
    }
  }

  async updateProfile(profileData: Partial<User>): Promise<{ success: boolean; user?: User; message?: string }> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/profile`, {
        method: 'PUT',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(profileData),
      });

      const data = await response.json();

      if (data.success && data.user) {
        // Kullanıcı bilgilerini güncelle
        localStorage.setItem('user', JSON.stringify(data.user));
        return { success: true, user: data.user };
      } else {
        return { success: false, message: data.message };
      }
    } catch (error) {
      return {
        success: false,
        message: error instanceof Error ? error.message : 'Profil güncellenemedi'
      };
    }
  }

  // Utility Methods
  isAuthenticated(): boolean {
    const token = localStorage.getItem('accessToken');
    if (!token) return false;

    try {
      // Token'ın süresi dolmuş mu kontrol et
      const expiresIn = localStorage.getItem('expiresIn');
      if (expiresIn) {
        const expirationTime = parseInt(expiresIn) * 1000; // milliseconds
        const currentTime = Date.now();
        
        // Token'ın ne zaman kaydedildiğini bilmiyoruz, bu yüzden basit kontrol
        // Gerçek uygulamada JWT decode edilmeli
        if (currentTime > expirationTime) {
          this.clearLocalStorage();
          return false;
        }
      }

      return true;
    } catch (error) {
      this.clearLocalStorage();
      return false;
    }
  }

  getCurrentUserFromStorage(): User | null {
    try {
      const userStr = localStorage.getItem('user');
      if (userStr) {
        const user = JSON.parse(userStr);
        console.log('👤 Current user from storage:', {
          username: user.username,
          role: user.role,
          id: user.id
        });
        return user;
      }
      console.log('👤 No user found in localStorage');
      return null;
    } catch (error) {
      console.error('👤 Error parsing user from localStorage:', error);
      // Corrupted user data varsa temizle
      localStorage.removeItem('user');
      return null;
    }
  }

  getToken(): string | null {
    return localStorage.getItem('accessToken');
  }

  getRefreshToken(): string | null {
    return localStorage.getItem('refreshToken');
  }

  clearLocalStorage(): void {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('tokenType');
    localStorage.removeItem('expiresIn');
    localStorage.removeItem('user');
  }

  // Token'ın süresinin dolup dolmadığını kontrol et
  isTokenExpired(): boolean {
    const token = localStorage.getItem('accessToken');
    if (!token) return true;

    try {
      // Bu basit bir kontrol, gerçek uygulamada JWT decode edilmeli
      const expiresIn = localStorage.getItem('expiresIn');
      if (expiresIn) {
        const expirationTime = parseInt(expiresIn) * 1000;
        return Date.now() > expirationTime;
      }
      return false;
    } catch (error) {
      return true;
    }
  }

  // Otomatik token yenileme
  async ensureValidToken(): Promise<boolean> {
    if (!this.isAuthenticated()) {
      return false;
    }

    if (this.isTokenExpired()) {
      const refreshResult = await this.refreshToken();
      return refreshResult.success;
    }

    return true;
  }
}

export const authService = new AuthService();