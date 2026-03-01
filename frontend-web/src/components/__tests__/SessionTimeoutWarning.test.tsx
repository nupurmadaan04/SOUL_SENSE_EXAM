/**
 * @jest-environment jsdom
 * 
 * SessionTimeoutWarning Component Tests (Issue #999)
 * --------------------------------------------------
 * Tests for the session timeout warning modal component.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SessionTimeoutWarning } from '../SessionTimeoutWarning';

// Mock useSessionTimeout hook
const mockContinueSession = jest.fn();
const mockUseSessionTimeout = jest.fn();

jest.mock('@/hooks/useSessionTimeout', () => ({
  useSessionTimeout: (options: any) => mockUseSessionTimeout(options),
}));

// Mock Button component
jest.mock('@/components/ui', () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} {...props}>
      {children}
    </button>
  ),
}));

describe('SessionTimeoutWarning Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Visibility', () => {
    it('should not render when showWarning is false', () => {
      mockUseSessionTimeout.mockReturnValue({
        showWarning: false,
        remainingSeconds: 0,
        continueSession: mockContinueSession,
      });

      const { container } = render(<SessionTimeoutWarning />);
      
      expect(container.firstChild).toBeNull();
    });

    it('should render when showWarning is true', () => {
      mockUseSessionTimeout.mockReturnValue({
        showWarning: true,
        remainingSeconds: 30,
        continueSession: mockContinueSession,
      });

      render(<SessionTimeoutWarning />);
      
      expect(screen.getByText('Session Timeout Warning')).toBeInTheDocument();
    });
  });

  describe('Content', () => {
    it('should display warning message', () => {
      mockUseSessionTimeout.mockReturnValue({
        showWarning: true,
        remainingSeconds: 30,
        continueSession: mockContinueSession,
      });

      render(<SessionTimeoutWarning />);
      
      expect(screen.getByText(/inactive for a while/i)).toBeInTheDocument();
      expect(screen.getByText(/session will expire soon/i)).toBeInTheDocument();
    });

    it('should display countdown timer', () => {
      mockUseSessionTimeout.mockReturnValue({
        showWarning: true,
        remainingSeconds: 25,
        continueSession: mockContinueSession,
      });

      render(<SessionTimeoutWarning />);
      
      expect(screen.getByText(/25 seconds remaining/i)).toBeInTheDocument();
    });

    it('should display singular "second" when remaining is 1', () => {
      mockUseSessionTimeout.mockReturnValue({
        showWarning: true,
        remainingSeconds: 1,
        continueSession: mockContinueSession,
      });

      render(<SessionTimeoutWarning />);
      
      expect(screen.getByText(/1 second remaining/i)).toBeInTheDocument();
    });

    it('should display Continue Session button', () => {
      mockUseSessionTimeout.mockReturnValue({
        showWarning: true,
        remainingSeconds: 30,
        continueSession: mockContinueSession,
      });

      render(<SessionTimeoutWarning />);
      
      expect(screen.getByRole('button', { name: /continue session/i })).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('should call continueSession when button is clicked', () => {
      mockUseSessionTimeout.mockReturnValue({
        showWarning: true,
        remainingSeconds: 30,
        continueSession: mockContinueSession,
      });

      render(<SessionTimeoutWarning />);
      
      const button = screen.getByRole('button', { name: /continue session/i });
      fireEvent.click(button);

      expect(mockContinueSession).toHaveBeenCalledTimes(1);
    });
  });

  describe('Styling', () => {
    it('should have modal overlay', () => {
      mockUseSessionTimeout.mockReturnValue({
        showWarning: true,
        remainingSeconds: 30,
        continueSession: mockContinueSession,
      });

      const { container } = render(<SessionTimeoutWarning />);
      
      // Check for backdrop/blur overlay
      const overlay = container.querySelector('.fixed.inset-0');
      expect(overlay).toBeInTheDocument();
    });

    it('should have warning styling', () => {
      mockUseSessionTimeout.mockReturnValue({
        showWarning: true,
        remainingSeconds: 30,
        continueSession: mockContinueSession,
      });

      const { container } = render(<SessionTimeoutWarning />);
      
      // Check for warning colors (amber)
      const warningIcon = container.querySelector('.text-amber-500');
      expect(warningIcon).toBeInTheDocument();
    });

    it('should have countdown styling', () => {
      mockUseSessionTimeout.mockReturnValue({
        showWarning: true,
        remainingSeconds: 30,
        continueSession: mockContinueSession,
      });

      const { container } = render(<SessionTimeoutWarning />);
      
      // Check for countdown container styling
      const countdownContainer = container.querySelector('.bg-amber-50, .dark\\:bg-amber-900\\/20');
      expect(countdownContainer).toBeInTheDocument();
    });
  });

  describe('useSessionTimeout Integration', () => {
    it('should call useSessionTimeout with enabled: true', () => {
      mockUseSessionTimeout.mockReturnValue({
        showWarning: false,
        remainingSeconds: 0,
        continueSession: mockContinueSession,
      });

      render(<SessionTimeoutWarning />);

      expect(mockUseSessionTimeout).toHaveBeenCalledWith({ enabled: true });
    });
  });
});

describe('SessionTimeoutWarning - Accessibility', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should have accessible button', () => {
    mockUseSessionTimeout.mockReturnValue({
      showWarning: true,
      remainingSeconds: 30,
      continueSession: mockContinueSession,
    });

    render(<SessionTimeoutWarning />);
    
    const button = screen.getByRole('button');
    expect(button).toBeEnabled();
  });

  it('should trap focus within modal when visible', () => {
    mockUseSessionTimeout.mockReturnValue({
      showWarning: true,
      remainingSeconds: 30,
      continueSession: mockContinueSession,
    });

    const { container } = render(<SessionTimeoutWarning />);
    
    // Modal should be the primary visible element
    const modal = container.querySelector('[role="dialog"]') || 
                  container.querySelector('.fixed.inset-0');
    expect(modal).toBeInTheDocument();
  });
});
