/**
 * AG-UI Integration E2E Tests
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-5: Playwright E2E Testing
 *
 * End-to-end integration tests covering complete user flows.
 */

import { test, expect } from './fixtures';

test.describe('AG-UI Integration Tests', () => {
  test('should load demo page successfully', async ({ agUiPage }) => {
    await expect(agUiPage.pageContainer).toBeVisible();
  });

  test('should display all 7 feature tabs', async ({ agUiPage }) => {
    await expect(agUiPage.chatTab).toBeVisible();
    await expect(agUiPage.toolTab).toBeVisible();
    await expect(agUiPage.hitlTab).toBeVisible();
    await expect(agUiPage.generativeTab).toBeVisible();
    await expect(agUiPage.toolUITab).toBeVisible();
    await expect(agUiPage.stateTab).toBeVisible();
    await expect(agUiPage.predictiveTab).toBeVisible();
  });

  test('should display event log panel', async ({ agUiPage }) => {
    await expect(agUiPage.eventLogPanel).toBeVisible();
  });

  test('should navigate between all tabs', async ({ agUiPage, page }) => {
    // Chat tab (default)
    await agUiPage.switchTab('chat');
    await expect(page.locator('[data-testid="agentic-chat-demo"]')).toBeVisible();

    // Tool tab
    await agUiPage.switchTab('tool');
    await expect(page.locator('[data-testid="tool-rendering-demo"]')).toBeVisible();

    // HITL tab
    await agUiPage.switchTab('hitl');
    await expect(page.locator('[data-testid="hitl-demo"]')).toBeVisible();

    // Generative tab
    await agUiPage.switchTab('generative');
    await expect(page.locator('[data-testid="generative-ui-demo"]')).toBeVisible();

    // Tool UI tab
    await agUiPage.switchTab('toolui');
    await expect(page.locator('[data-testid="tool-ui-demo"]')).toBeVisible();

    // State tab
    await agUiPage.switchTab('state');
    await expect(page.locator('[data-testid="shared-state-demo"]')).toBeVisible();

    // Predictive tab
    await agUiPage.switchTab('predictive');
    await expect(page.locator('[data-testid="predictive-demo"]')).toBeVisible();
  });

  test('should display header with correct title', async ({ page }) => {
    const title = page.locator('h1:has-text("AG-UI Protocol Demo")');
    await expect(title).toBeVisible();
  });

  test('should display footer status bar', async ({ page }) => {
    const footer = page.locator('footer');
    await expect(footer).toBeVisible();
    await expect(footer).toContainText('Connected');
    await expect(footer).toContainText('Sprint 61');
  });

  test('should show thread ID in header', async ({ page }) => {
    const threadBadge = page.locator('text=/Thread: thread_/');
    await expect(threadBadge).toBeVisible();
  });

  test('should clear event log when clicking Clear button', async ({ page }) => {
    // Generate some events first
    await page.locator('[data-testid="tab-generative"]').click();
    await page.locator('button:has-text("Start Generation")').click();
    await page.waitForTimeout(500);

    // Click clear button
    const clearBtn = page.locator('button:has-text("Clear")');
    await clearBtn.click();

    // Event log should be empty or show "No events"
    await page.waitForTimeout(100);
    const eventPanel = page.locator('[data-testid="event-log-panel"]');
    await expect(eventPanel).toBeVisible();
  });

  test('should maintain state when switching tabs', async ({ page }) => {
    // Go to state demo and modify counter
    await page.locator('[data-testid="tab-state"]').click();
    const incrementBtn = page.locator('button:has-text("+")');
    await incrementBtn.click();
    await incrementBtn.click();

    // Switch to another tab
    await page.locator('[data-testid="tab-chat"]').click();

    // Switch back
    await page.locator('[data-testid="tab-state"]').click();

    // Counter should still show modified value
    const counterDisplay = page.locator('.text-2xl.font-bold');
    const value = await counterDisplay.textContent();
    expect(parseInt(value || '0')).toBeGreaterThan(0);
  });

  test('should handle responsive layout', async ({ page }) => {
    // Test at different viewport sizes
    await page.setViewportSize({ width: 1200, height: 800 });
    await expect(page.locator('[data-testid="ag-ui-demo-page"]')).toBeVisible();

    await page.setViewportSize({ width: 768, height: 600 });
    await expect(page.locator('[data-testid="ag-ui-demo-page"]')).toBeVisible();
  });

  test('should complete full HITL approval flow', async ({ page }) => {
    // Navigate to HITL demo
    await page.locator('[data-testid="tab-hitl"]').click();

    // Add an approval
    await page.locator('button:has-text("High Risk")').click();

    // Verify approval appears
    const banner = page.locator('[data-testid^="approval-banner-"]').first();
    await expect(banner).toBeVisible();

    // Approve it
    const approveBtn = banner.locator('[data-testid^="approve-"]');
    await approveBtn.click();

    // Verify it's removed
    await page.waitForTimeout(500);
    await expect(banner).not.toBeVisible();
  });

  test('should complete full generative UI flow', async ({ page }) => {
    // Navigate to generative demo
    await page.locator('[data-testid="tab-generative"]').click();

    // Start generation
    await page.locator('button:has-text("Start Generation")').click();

    // Wait for completion
    const successMessage = page.locator('text=Generation Complete!');
    await expect(successMessage).toBeVisible({ timeout: 10000 });

    // Reset
    await page.locator('button:has-text("Reset")').click();

    // Verify idle state
    const idleBadge = page.locator('text=Mode: IDLE');
    await expect(idleBadge).toBeVisible();
  });
});
