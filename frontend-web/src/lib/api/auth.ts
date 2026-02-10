import { apiClient } from './client';

export const authApi = {
  async login(data: {
    username: string;
    password: string;
    captcha_input?: string;
    session_id?: string;
  }): Promise<{ access_token: string; pre_auth_token?: string }> {
    return apiClient('/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
  },

  async login2FA(data: {
    pre_auth_token: string;
    code: string;
  }): Promise<{ access_token: string }> {
    return apiClient('/auth/login/2fa', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
  },

  async initiatePasswordReset(email: string): Promise<{ message: string }> {
    return apiClient('/auth/password-reset/initiate', {
      method: 'POST',
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
  },
};
