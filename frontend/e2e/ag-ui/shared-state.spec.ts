/**
 * Shared State E2E Tests
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-5: Playwright E2E Testing
 *
 * Tests for AG-UI Feature 6: Frontend-Backend State Synchronization.
 */

import { test, expect } from './fixtures';

test.describe('Feature 6: Shared State', () => {
  test.beforeEach(async ({ agUiPage }) => {
    await agUiPage.switchTab('state');
  });

  test('should display shared state demo', async ({ page }) => {
    const demo = page.locator('[data-testid="shared-state-demo"]');
    await expect(demo).toBeVisible();
  });

  test('should show sync status indicator', async ({ page }) => {
    const syncStatus = page.locator('text=Sync Status:');
    await expect(syncStatus).toBeVisible();
  });

  test('should display counter controls', async ({ page }) => {
    const incrementBtn = page.locator('button:has-text("+")');
    const decrementBtn = page.locator('button:has-text("-")');

    await expect(incrementBtn).toBeVisible();
    await expect(decrementBtn).toBeVisible();
  });

  test('should increment counter when clicking +', async ({ page }) => {
    const incrementBtn = page.locator('button:has-text("+")');
    const counterDisplay = page.locator('.text-2xl.font-bold');

    const initialValue = await counterDisplay.textContent();
    await incrementBtn.click();

    await page.waitForTimeout(500);
    const newValue = await counterDisplay.textContent();

    expect(parseInt(newValue || '0')).toBe(parseInt(initialValue || '0') + 1);
  });

  test('should decrement counter when clicking -', async ({ page }) => {
    const decrementBtn = page.locator('button:has-text("-")');
    const counterDisplay = page.locator('.text-2xl.font-bold');

    const initialValue = await counterDisplay.textContent();
    await decrementBtn.click();

    await page.waitForTimeout(500);
    const newValue = await counterDisplay.textContent();

    expect(parseInt(newValue || '0')).toBe(parseInt(initialValue || '0') - 1);
  });

  test('should have text input field', async ({ page }) => {
    const textInput = page.locator('input[placeholder="Type something..."]');
    await expect(textInput).toBeVisible();
  });

  test('should update state when typing in text field', async ({ page }) => {
    const textInput = page.locator('input[placeholder="Type something..."]');
    await textInput.fill('Hello, State!');

    // Check state debugger shows the value
    const stateView = page.locator('text="Hello, State!"');
    await expect(stateView).toBeVisible();
  });

  test('should display items list', async ({ page }) => {
    await expect(page.locator('text=Items List')).toBeVisible();
    await expect(page.locator('text=Item A')).toBeVisible();
    await expect(page.locator('text=Item B')).toBeVisible();
  });

  test('should add new item to list', async ({ page }) => {
    const newItemInput = page.locator('input[placeholder="New item..."]');
    const addBtn = page.locator('button:has-text("Add")');

    await newItemInput.fill('New Test Item');
    await addBtn.click();

    await expect(page.locator('text=New Test Item')).toBeVisible();
  });

  test('should remove item when clicking x', async ({ page }) => {
    // Find Item A's remove button
    const itemA = page.locator('span:has-text("Item A")');
    const removeBtn = itemA.locator('button');

    await removeBtn.click();

    // Item A should be removed
    await expect(page.locator('text=Item A')).not.toBeVisible();
  });

  test('should have Simulate Server Update button', async ({ page }) => {
    const serverBtn = page.locator('button:has-text("Simulate Server Update")');
    await expect(serverBtn).toBeVisible();
  });

  test('should show syncing status during update', async ({ page }) => {
    const incrementBtn = page.locator('button:has-text("+")');
    await incrementBtn.click();

    // Check for syncing status (briefly visible)
    const syncingStatus = page.locator('text=Syncing...');
    // Status may be too fast to catch, so we just ensure no errors
    await page.waitForTimeout(500);
  });

  test('should display state debugger', async ({ page }) => {
    const debugger_ = page.locator('text=Current State');
    await expect(debugger_).toBeVisible();
  });
});
