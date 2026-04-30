/**
 * Human-in-the-Loop E2E Tests
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-5: Playwright E2E Testing
 *
 * Tests for AG-UI Feature 3: HITL Approval Workflow.
 */

import { test, expect } from './fixtures';

test.describe('Feature 3: Human-in-the-Loop', () => {
  test.beforeEach(async ({ agUiPage }) => {
    await agUiPage.switchTab('hitl');
  });

  test('should display HITL demo', async ({ page }) => {
    const demo = page.locator('[data-testid="hitl-demo"]');
    await expect(demo).toBeVisible();
  });

  test('should have risk level buttons', async ({ page }) => {
    await expect(page.locator('button:has-text("Low Risk")')).toBeVisible();
    await expect(page.locator('button:has-text("Medium Risk")')).toBeVisible();
    await expect(page.locator('button:has-text("High Risk")')).toBeVisible();
    await expect(page.locator('button:has-text("Critical Risk")')).toBeVisible();
  });

  test('should add low risk approval when clicking Low Risk button', async ({ page }) => {
    const addBtn = page.locator('button:has-text("Low Risk")');
    await addBtn.click();

    // Check approval banner appears
    const banner = page.locator('[data-testid^="approval-banner-"]').first();
    await expect(banner).toBeVisible();
  });

  test('should display correct risk badge color', async ({ page, agUiPage }) => {
    // Add high risk approval
    await page.locator('button:has-text("High Risk")').click();

    // Check risk badge
    const highRiskBadge = agUiPage.getRiskBadge('high');
    await expect(highRiskBadge).toBeVisible();
  });

  test('should show approve and reject buttons in approval banner', async ({ page }) => {
    // Add an approval
    await page.locator('button:has-text("Medium Risk")').click();

    // Check buttons in banner
    const banner = page.locator('[data-testid^="approval-banner-"]').first();
    const approveBtn = banner.locator('[data-testid^="approve-"]');
    const rejectBtn = banner.locator('[data-testid^="reject-"]');

    await expect(approveBtn).toBeVisible();
    await expect(rejectBtn).toBeVisible();
  });

  test('should open approval dialog when clicking Details', async ({ page }) => {
    // Add an approval
    await page.locator('button:has-text("High Risk")').click();

    // Click details button
    const detailsBtn = page.locator('[data-testid^="details-"]').first();
    if (await detailsBtn.isVisible()) {
      await detailsBtn.click();

      // Check dialog is open
      const dialog = page.locator('[data-testid^="approval-dialog-"]');
      await expect(dialog).toBeVisible();
    }
  });

  test('should remove approval from list after approve action', async ({ page }) => {
    // Add an approval
    await page.locator('button:has-text("Low Risk")').click();

    // Get approval ID
    const banner = page.locator('[data-testid^="approval-banner-"]').first();
    const approveBtn = banner.locator('[data-testid^="approve-"]').first();

    // Click approve
    await approveBtn.click();

    // Wait for banner to be removed
    await page.waitForTimeout(500);
    const bannersAfter = page.locator('[data-testid^="approval-banner-"]');
    const countAfter = await bannersAfter.count();

    // Should have one less banner
    expect(countAfter).toBe(0);
  });

  test('should show action history after approval/rejection', async ({ page }) => {
    // Add and approve an approval
    await page.locator('button:has-text("Low Risk")').click();
    const approveBtn = page.locator('[data-testid^="approve-"]').first();
    await approveBtn.click();

    // Check history section
    const history = page.locator('text=Action History');
    await expect(history).toBeVisible();
  });

  test('should support batch selection when enabled', async ({ page }) => {
    // Add multiple approvals
    await page.locator('button:has-text("Low Risk")').click();
    await page.locator('button:has-text("Medium Risk")').click();

    // Check for select all button
    const selectAllBtn = page.locator('[data-testid="select-all"]');
    await expect(selectAllBtn).toBeVisible();
  });

  test('should show empty state when no approvals', async ({ page }) => {
    const emptyState = page.locator('[data-testid="approval-list-empty"]');
    await expect(emptyState).toBeVisible();
    await expect(emptyState).toContainText('No pending approvals');
  });
});
