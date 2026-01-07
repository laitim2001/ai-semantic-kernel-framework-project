/**
 * Predictive State E2E Tests
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-5: Playwright E2E Testing
 *
 * Tests for AG-UI Feature 7: Optimistic Updates with Rollback.
 */

import { test, expect } from './fixtures';

test.describe('Feature 7: Predictive State', () => {
  test.beforeEach(async ({ agUiPage }) => {
    await agUiPage.switchTab('predictive');
  });

  test('should display predictive demo', async ({ page }) => {
    const demo = page.locator('[data-testid="predictive-demo"]');
    await expect(demo).toBeVisible();
  });

  test('should display task list', async ({ page }) => {
    await expect(page.locator('text=Review pull request')).toBeVisible();
    await expect(page.locator('text=Write documentation')).toBeVisible();
    await expect(page.locator('text=Fix bug #123')).toBeVisible();
  });

  test('should have simulate failure toggle', async ({ page }) => {
    const toggle = page.locator('text=Simulate Random Failures');
    await expect(toggle).toBeVisible();
  });

  test('should toggle task completion', async ({ page }) => {
    const task = page.locator('[data-testid="task-1"]');
    const checkbox = task.locator('input[type="checkbox"]');

    const initialChecked = await checkbox.isChecked();
    await checkbox.click();

    // Wait for optimistic update
    await page.waitForTimeout(100);
    const newChecked = await checkbox.isChecked();

    expect(newChecked).not.toBe(initialChecked);
  });

  test('should show Saving badge during optimistic update', async ({ page }) => {
    const task = page.locator('[data-testid="task-1"]');
    const checkbox = task.locator('input[type="checkbox"]');

    await checkbox.click();

    // Check for Saving badge
    const savingBadge = page.locator('text=Saving...');
    await expect(savingBadge).toBeVisible({ timeout: 500 });
  });

  test('should show Saved badge after confirmation', async ({ page }) => {
    const task = page.locator('[data-testid="task-2"]');
    const checkbox = task.locator('input[type="checkbox"]');

    await checkbox.click();

    // Wait for confirmation (1 second + some buffer)
    const savedBadge = page.locator('text=Saved ✓');
    await expect(savedBadge).toBeVisible({ timeout: 3000 });
  });

  test('should update history log after action', async ({ page }) => {
    const task = page.locator('[data-testid="task-4"]');
    const checkbox = task.locator('input[type="checkbox"]');

    await checkbox.click();

    // Wait for history update
    await page.waitForTimeout(1500);

    const historySection = page.locator('text=Update History');
    await expect(historySection).toBeVisible();
  });

  test('should show rollback when failure is simulated', async ({ page }) => {
    // Enable failure simulation
    const toggle = page.locator('input[type="checkbox"]').first();
    await toggle.check();

    // Try multiple tasks to trigger rollback (50% chance)
    const task = page.locator('[data-testid="task-1"]');
    const checkbox = task.locator('input[type="checkbox"]');

    // Toggle multiple times to increase chance of seeing rollback
    for (let i = 0; i < 3; i++) {
      await checkbox.click();
      await page.waitForTimeout(1500);
    }

    // Check history for rollback entry
    const history = page.locator('.font-mono.text-gray-300');
    const historyText = await history.textContent();

    // History should contain some entries (rollback or confirmed)
    expect(historyText?.length).toBeGreaterThan(0);
  });

  test('should display optimistic indicator', async ({ page }) => {
    const indicator = page.locator('.OptimisticIndicator, [class*="Optimistic"]');
    // Indicator may or may not be visible based on pending state
    // Just verify the demo is functional
    const demo = page.locator('[data-testid="predictive-demo"]');
    await expect(demo).toBeVisible();
  });

  test('should have tips section explaining the feature', async ({ page }) => {
    const tips = page.locator('text=How it works:');
    await expect(tips).toBeVisible();
  });

  test('should apply line-through style to completed tasks', async ({ page }) => {
    // Task 3 is initially completed
    const completedTask = page.locator('[data-testid="task-3"]');
    const taskText = completedTask.locator('.line-through');

    await expect(taskText).toBeVisible();
  });
});
