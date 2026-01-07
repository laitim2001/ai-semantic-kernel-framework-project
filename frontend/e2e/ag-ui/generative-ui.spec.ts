/**
 * Generative UI E2E Tests
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-5: Playwright E2E Testing
 *
 * Tests for AG-UI Feature 4: Dynamic UI Generation.
 */

import { test, expect } from './fixtures';

test.describe('Feature 4: Generative UI', () => {
  test.beforeEach(async ({ agUiPage }) => {
    await agUiPage.switchTab('generative');
  });

  test('should display generative UI demo', async ({ page }) => {
    const demo = page.locator('[data-testid="generative-ui-demo"]');
    await expect(demo).toBeVisible();
  });

  test('should have Start Generation button', async ({ page }) => {
    const startBtn = page.locator('button:has-text("Start Generation")');
    await expect(startBtn).toBeVisible();
    await expect(startBtn).toBeEnabled();
  });

  test('should have Reset button disabled initially', async ({ page }) => {
    const resetBtn = page.locator('button:has-text("Reset")');
    await expect(resetBtn).toBeVisible();
    await expect(resetBtn).toBeDisabled();
  });

  test('should show idle mode badge initially', async ({ page }) => {
    const badge = page.locator('text=Mode: IDLE');
    await expect(badge).toBeVisible();
  });

  test('should start generation and show progress', async ({ page }) => {
    // Click start
    const startBtn = page.locator('button:has-text("Start Generation")');
    await startBtn.click();

    // Check mode changes
    const analyzingBadge = page.locator('text=Mode: ANALYZING');
    await expect(analyzingBadge).toBeVisible({ timeout: 2000 });
  });

  test('should show step indicators during generation', async ({ page }) => {
    // Start generation
    await page.locator('button:has-text("Start Generation")').click();

    // Check first step becomes active
    const firstStep = page.locator('text=Analyzing request').first();
    const parentDiv = firstStep.locator('xpath=ancestor::div[contains(@class, "rounded-lg")]').first();

    // Wait for step to be highlighted
    await page.waitForTimeout(500);
    await expect(parentDiv).toBeVisible();
  });

  test('should complete generation and show success message', async ({ page }) => {
    // Start generation
    await page.locator('button:has-text("Start Generation")').click();

    // Wait for completion (up to 10 seconds)
    const successMessage = page.locator('text=Generation Complete!');
    await expect(successMessage).toBeVisible({ timeout: 10000 });
  });

  test('should enable Reset button after generation starts', async ({ page }) => {
    await page.locator('button:has-text("Start Generation")').click();

    const resetBtn = page.locator('button:has-text("Reset")');
    await expect(resetBtn).toBeEnabled();
  });

  test('should reset to idle state when clicking Reset', async ({ page }) => {
    // Start and then reset
    await page.locator('button:has-text("Start Generation")').click();
    await page.waitForTimeout(500);
    await page.locator('button:has-text("Reset")').click();

    // Check idle mode
    const idleBadge = page.locator('text=Mode: IDLE');
    await expect(idleBadge).toBeVisible();
  });

  test('should display progress bar', async ({ page }) => {
    await page.locator('button:has-text("Start Generation")').click();

    // Check progress bar container
    const progressBar = page.locator('.bg-blue-600').first();
    await expect(progressBar).toBeVisible();
  });

  test('should show all four progress steps', async ({ page }) => {
    await expect(page.locator('text=Analyzing request')).toBeVisible();
    await expect(page.locator('text=Generating structure')).toBeVisible();
    await expect(page.locator('text=Applying styles')).toBeVisible();
    await expect(page.locator('text=Finalizing output')).toBeVisible();
  });
});
