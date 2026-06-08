// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import App from '../src/App';
import React from 'react';

// Mock Tauri APIs
vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn().mockResolvedValue('connected'),
}));

vi.mock('@tauri-apps/api/event', () => ({
  listen: vi.fn().mockResolvedValue(vi.fn()),
}));

describe('Dashboard UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders executive dashboard layout and header', async () => {
    render(<App />);
    expect(screen.getByText('TRUEVOICE // EXECUTIVE SECURITY')).toBeTruthy();
  });

  it('can trigger mock alert simulation and display detail modal', async () => {
    render(<App />);
    
    // Check initial system state
    expect(screen.getByText('SYSTEM SECURE')).toBeTruthy();
    
    // Click simulated alert button
    const testButton = screen.getByText('TEST ALERT');
    fireEvent.click(testButton);
    
    // Screen should update state
    expect(screen.getByText('BREACH THREAT DETECTED')).toBeTruthy();
    
    // Details modal should be displayed
    expect(screen.getByText('SECURITY ALERT DETECTED')).toBeTruthy();
    expect(screen.getAllByText('OTP Theft / Phishing').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/We detected a suspicious login/).length).toBeGreaterThan(0);
    
    // Close modal
    const closeButton = screen.getByText('Acknowledge Alert');
    fireEvent.click(closeButton);
    
    // Modal should disappear but threat remains in the log history
    expect(screen.queryByText('SECURITY ALERT DETECTED')).toBeNull();
  });
});
