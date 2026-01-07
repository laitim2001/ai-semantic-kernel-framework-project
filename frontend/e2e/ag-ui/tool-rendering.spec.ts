/**
 * Tool Rendering E2E Tests
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-5: Playwright E2E Testing
 *
 * Tests for AG-UI Feature 2: Tool Result Rendering.
 */

import { test, expect } from './fixtures';

test.describe('Feature 2: Tool Rendering', () => {
  test.beforeEach(async ({ agUiPage }) => {
    await agUiPage.switchTab('tool');
  });

  test('should display tool rendering demo', async ({ page }) => {
    const demo = page.locator('[data-testid="tool-rendering-demo"]');
    await expect(demo).toBeVisible();
  });

  test('should show multiple tool call cards', async ({ page }) => {
    const cards = page.locator('[data-testid^="tool-call-card-"]');
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should display completed tool with result', async ({ page }) => {
    // Find a completed tool card
    const completedCard = page.locator('[data-testid^="tool-call-card-"]').filter({
      hasText: 'Completed',
    }).first();

    await expect(completedCard).toBeVisible();
  });

  test('should display failed tool with error styling', async ({ page }) => {
    // Find a failed tool card
    const failedCard = page.locator('[data-testid^="tool-call-card-"]').filter({
      hasText: 'Failed',
    }).first();

    await expect(failedCard).toBeVisible();
  });

  test('should display pending approval tool with action buttons', async ({ page }) => {
    // Find a tool requiring approval
    const pendingCard = page.locator('[data-testid^="tool-call-card-"]').filter({
      hasText: 'Requires Approval',
    }).first();

    if (await pendingCard.isVisible()) {
      const approveBtn = pendingCard.locator('[data-testid^="approve-"]');
      const rejectBtn = pendingCard.locator('[data-testid^="reject-"]');

      await expect(approveBtn).toBeVisible();
      await expect(rejectBtn).toBeVisible();
    }
  });

  test('should expand tool card to show details', async ({ page }) => {
    const card = page.locator('[data-testid^="tool-call-card-"]').first();
    await card.click();

    // Check if arguments section is visible after expansion
    const argsSection = card.locator('text=Arguments');
    await expect(argsSection).toBeVisible();
  });

  test('should have reset demo button', async ({ page }) => {
    const resetBtn = page.locator('button:has-text("Reset Demo")');
    await expect(resetBtn).toBeVisible();
  });

  test('should reset demo state when clicking reset', async ({ page }) => {
    // Click reset button
    const resetBtn = page.locator('button:has-text("Reset Demo")');
    await resetBtn.click();

    // Verify cards are back to initial state
    const cards = page.locator('[data-testid^="tool-call-card-"]');
    const count = await cards.count();
    expect(count).toBe(4); // Initial sample count
  });
});
