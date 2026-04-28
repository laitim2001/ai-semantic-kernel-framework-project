/**
 * Tool-based UI E2E Tests
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-5: Playwright E2E Testing
 *
 * Tests for AG-UI Feature 5: Tool-based Dynamic UI.
 */

import { test, expect } from './fixtures';

test.describe('Feature 5: Tool-based UI', () => {
  test.beforeEach(async ({ agUiPage }) => {
    await agUiPage.switchTab('toolui');
  });

  test('should display tool UI demo', async ({ page }) => {
    const demo = page.locator('[data-testid="tool-ui-demo"]');
    await expect(demo).toBeVisible();
  });

  test('should have UI type selector buttons', async ({ page }) => {
    await expect(page.locator('button:has-text("Form")')).toBeVisible();
    await expect(page.locator('button:has-text("Chart")')).toBeVisible();
    await expect(page.locator('button:has-text("Card")')).toBeVisible();
    await expect(page.locator('button:has-text("Table")')).toBeVisible();
  });

  test('should display form by default', async ({ page }) => {
    const formTitle = page.locator('text=User Registration');
    await expect(formTitle).toBeVisible();
  });

  test('should have form input fields', async ({ page }) => {
    // Check for form fields
    await expect(page.locator('text=Full Name')).toBeVisible();
    await expect(page.locator('text=Email')).toBeVisible();
    await expect(page.locator('text=Role')).toBeVisible();
  });

  test('should switch to chart view', async ({ page }) => {
    await page.locator('button:has-text("Chart")').click();

    // Check chart title
    const chartTitle = page.locator('text=Monthly Revenue');
    await expect(chartTitle).toBeVisible();
  });

  test('should switch to card view', async ({ page }) => {
    await page.locator('button:has-text("Card")').click();

    // Check card content
    await expect(page.locator('text=Project Alpha')).toBeVisible();
    await expect(page.locator('text=Project Beta')).toBeVisible();
  });

  test('should switch to table view', async ({ page }) => {
    await page.locator('button:has-text("Table")').click();

    // Check table headers
    await expect(page.locator('text=User List')).toBeVisible();
    await expect(page.locator('th:has-text("Name")')).toBeVisible();
    await expect(page.locator('th:has-text("Email")')).toBeVisible();
  });

  test('should display table data rows', async ({ page }) => {
    await page.locator('button:has-text("Table")').click();

    // Check for data
    await expect(page.locator('text=Alice Chen')).toBeVisible();
    await expect(page.locator('text=Bob Wang')).toBeVisible();
  });

  test('should have form submit button', async ({ page }) => {
    const submitBtn = page.locator('button:has-text("Register")');
    await expect(submitBtn).toBeVisible();
  });

  test('should show submitted data after form submission', async ({ page }) => {
    // Fill form
    await page.locator('input[name="name"]').fill('Test User');
    await page.locator('input[name="email"]').fill('test@example.com');

    // Submit
    await page.locator('button:has-text("Register")').click();

    // Check submitted data display
    const submittedData = page.locator('text=Submitted Data');
    await expect(submittedData).toBeVisible();
  });

  test('should display card action buttons', async ({ page }) => {
    await page.locator('button:has-text("Card")').click();

    const viewDetailsBtn = page.locator('button:has-text("View Details")').first();
    await expect(viewDetailsBtn).toBeVisible();
  });
});
