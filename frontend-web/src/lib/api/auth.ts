import { apiClient } from './client';

export const authApi = {
  async login(data: {
    username: string;
    password: string;
    captcha_input?: string;
    session_id?: string;
  }): Promise<{
    access_token: string;
    pre_auth_token?: string;
    refresh_token?: string;
    email?: string;
    username?: string;
    id?: number;
    created_at?: string;
    warnings?: any[];
    onboarding_completed?: boolean;
  }> {
    return apiClient('/auth/login', {
      method: 'POST',
      skipAuth: true,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        identifier: data.username,
        password: data.password,
        captcha_input: data.captcha_input,
        session_id: data.session_id,
      }),
    });
  },

  async login2FA(data: { pre_auth_token: string; code: string }): Promise<{
    access_token: string;
    email?: string;
    username?: string;
    id?: number;
    created_at?: string;
    onboarding_completed?: boolean;
  }> {
    return apiClient('/auth/login/2fa', {
      method: 'POST',
      skipAuth: true,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
  },

  async initiatePasswordReset(email: string): Promise<{ message: string }> {
    return apiClient('/auth/password-reset/initiate', {
      method: 'POST',
      skipAuth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
  },

  async completePasswordReset(data: {
    email: string;
    otp_code: string;
    new_password: string;
  }): Promise<{ message: string }> {
    return apiClient('/auth/password-reset/complete', {
      method: 'POST',
      skipAuth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },
  async getCaptcha(): Promise<{ captcha_code: string; session_id: string }> {
    try {
      return await apiClient(`/auth/captcha?t=${Date.now()}`, {
        method: 'GET',
        skipAuth: true,
        timeout: 5000,
      });
    } catch (err) {
      console.warn('Backend CAPTCHA fetch failed, generating client fallback CAPTCHA:', err);
      const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
      let code = '';
      for (let i = 0; i < 5; i++) {
        code += chars.charAt(Math.floor(Math.random() * chars.length));
      }
      return {
        captcha_code: code,
        session_id: `client_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      };
    }
  },

  async checkUsernameAvailability(
    username: string
  ): Promise<{ available: boolean; message: string }> {
    return apiClient(`/auth/check-username?username=${encodeURIComponent(username)}`, {
      method: 'GET',
      skipAuth: true,
    });
  },

  async register(data: {
    username: string;
    password: string;
    email: string;
    first_name: string;
    last_name: string;
    age: number;
    gender: string;
  }): Promise<{ message: string }> {
    // Map camelCase to snake_case for backend
    const payload = {
      username: data.username,
      password: data.password,
      email: data.email,
      first_name: data.first_name,
      last_name: data.last_name,
      age: data.age,
      gender: data.gender,
    };
    return apiClient('/auth/register', {
      method: 'POST',
      skipAuth: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  },

  async refreshToken(): Promise<{ access_token: string }> {
    return apiClient('/auth/refresh', {
      method: 'POST',
      skipAuth: true,
    });
  },

  async logout(): Promise<void> {
    return apiClient('/auth/logout', {
      method: 'POST',
      skipAuth: true,
      credentials: 'include',
    });
  },
  async oauthLogin(data: {
    provider: string;
    idToken?: string;
    accessToken?: string;
  }): Promise<{
    access_token: string;
    email?: string;
    username?: string;
    id?: number;
    created_at?: string;
    onboarding_completed?: boolean;
    is_admin?: boolean;
  }> {
    const formData = new URLSearchParams();
    formData.append('provider', data.provider);
    if (data.idToken) formData.append('id_token', data.idToken);
    if (data.accessToken) formData.append('access_token', data.accessToken);

    return apiClient('/auth/oauth/login', {
      method: 'POST',
      skipAuth: true,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });
  },
};
