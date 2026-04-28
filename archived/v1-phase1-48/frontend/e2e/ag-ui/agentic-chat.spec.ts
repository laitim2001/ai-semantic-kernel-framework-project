/**
 * Agentic Chat E2E Tests
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-5: Playwright E2E Testing
 *
 * Tests for AG-UI Feature 1: Agentic Chat functionality.
 */

import { test, expect } from './fixtures';

test.describe('Feature 1: Agentic Chat', () => {
  test.beforeEach(async ({ agUiPage }) => {
    await agUiPage.switchTab('chat');
  });

  test('should display chat container', async ({ agUiPage }) => {
    await expect(agUiPage.chatContainer).toBeVisible();
  });

  test('should have message input and send button', async ({ agUiPage }) => {
    await expect(agUiPage.messageInput).toBeVisible();
    await expect(agUiPage.sendButton).toBeVisible();
  });

  test('should disable send button when input is empty', async ({ agUiPage }) => {
    await expect(agUiPage.sendButton).toBeDisabled();
  });

  test('should enable send button when input has text', async ({ agUiPage }) => {
    await agUiPage.messageInput.fill('Hello, AI!');
    await expect(agUiPage.sendButton).toBeEnabled();
  });

  test('should send message and display user bubble', async ({ agUiPage }) => {
    const message = 'Test message from E2E';
    await agUiPage.sendMessage(message);

    // Check user message is displayed
    const userMessage = agUiPage.page.locator('[data-testid="message-bubble-user"]').last();
    await expect(userMessage).toContainText('You');
  });

  test('should clear input after sending message', async ({ agUiPage }) => {
    await agUiPage.sendMessage('Test message');
    await expect(agUiPage.messageInput).toHaveValue('');
  });

  test('should show connection status badge', async ({ agUiPage }) => {
    const statusBadge = agUiPage.page.locator('[data-testid="chat-container"]').locator('.badge, [class*="Badge"]').first();
    await expect(statusBadge).toBeVisible();
  });

  test('should display empty state when no messages', async ({ page }) => {
    // Navigate to a fresh page to ensure no messages
    await page.goto('/ag-ui-demo');
    await page.locator('[data-testid="tab-chat"]').click();

    const emptyState = page.locator('[data-testid="chat-container"]').locator('text=Start a conversation');
    await expect(emptyState).toBeVisible();
  });

  test('should support Enter key to send message', async ({ agUiPage }) => {
    await agUiPage.messageInput.fill('Enter key test');
    await agUiPage.messageInput.press('Enter');

    await expect(agUiPage.messageInput).toHaveValue('');
  });

  test('should support Shift+Enter for new line', async ({ agUiPage }) => {
    await agUiPage.messageInput.fill('Line 1');
    await agUiPage.messageInput.press('Shift+Enter');
    await agUiPage.messageInput.type('Line 2');

    const value = await agUiPage.messageInput.inputValue();
    expect(value).toContain('\n');
  });
});
