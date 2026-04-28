/**
 * AG-UI E2E Test Fixtures
 *
 * Sprint 61: AG-UI Frontend Integration
 * S61-5: Playwright E2E Testing
 *
 * Custom test fixtures and page object for AG-UI demo page testing.
 */

import { test as base, expect, Page, Locator } from '@playwright/test';

/**
 * AG-UI Demo Page Object
 *
 * Encapsulates common page interactions for testing.
 */
export class AGUITestPage {
  readonly page: Page;

  // Main elements
  readonly pageContainer: Locator;
  readonly tabNavigation: Locator;
  readonly eventLogPanel: Locator;

  // Tabs
  readonly chatTab: Locator;
  readonly toolTab: Locator;
  readonly hitlTab: Locator;
  readonly generativeTab: Locator;
  readonly toolUITab: Locator;
  readonly stateTab: Locator;
  readonly predictiveTab: Locator;

  // Chat elements
  readonly messageInput: Locator;
  readonly sendButton: Locator;
  readonly chatContainer: Locator;

  // Approval elements
  readonly approvalDialog: Locator;
  readonly approvalBanner: Locator;

  constructor(page: Page) {
    this.page = page;

    // Main elements
    this.pageContainer = page.locator('[data-testid="ag-ui-demo-page"]');
    this.tabNavigation = page.locator('[data-testid^="tab-"]');
    this.eventLogPanel = page.locator('[data-testid="event-log-panel"]');

    // Tabs
    this.chatTab = page.locator('[data-testid="tab-chat"]');
    this.toolTab = page.locator('[data-testid="tab-tool"]');
    this.hitlTab = page.locator('[data-testid="tab-hitl"]');
    this.generativeTab = page.locator('[data-testid="tab-generative"]');
    this.toolUITab = page.locator('[data-testid="tab-toolui"]');
    this.stateTab = page.locator('[data-testid="tab-state"]');
    this.predictiveTab = page.locator('[data-testid="tab-predictive"]');

    // Chat elements
    this.messageInput = page.locator('[data-testid="message-input-textarea"]');
    this.sendButton = page.locator('[data-testid="send-button"]');
    this.chatContainer = page.locator('[data-testid="chat-container"]');

    // Approval elements
    this.approvalDialog = page.locator('[data-testid^="approval-dialog-"]');
    this.approvalBanner = page.locator('[data-testid^="approval-banner-"]');
  }

  /**
   * Navigate to AG-UI demo page
   */
  async goto() {
    await this.page.goto('/ag-ui-demo');
    await this.pageContainer.waitFor({ state: 'visible' });
  }

  /**
   * Switch to a specific feature tab
   */
  async switchTab(tabId: string) {
    const tab = this.page.locator(`[data-testid="tab-${tabId}"]`);
    await tab.click();
    await this.page.waitForTimeout(300); // Wait for tab transition
  }

  /**
   * Send a chat message
   */
  async sendMessage(text: string) {
    await this.messageInput.fill(text);
    await this.sendButton.click();
  }

  /**
   * Wait for assistant response
   */
  async waitForAssistantMessage() {
    await this.page.locator('[data-testid="message-bubble-assistant"]').waitFor({
      state: 'visible',
      timeout: 10000,
    });
  }

  /**
   * Get event log count
   */
  async getEventCount(): Promise<number> {
    const events = this.page.locator('[data-testid^="event-"]');
    return events.count();
  }

  /**
   * Click approve button for a tool call
   */
  async approveToolCall(toolCallId: string) {
    const approveBtn = this.page.locator(`[data-testid="approve-${toolCallId}"]`);
    await approveBtn.click();
  }

  /**
   * Click reject button for a tool call
   */
  async rejectToolCall(toolCallId: string) {
    const rejectBtn = this.page.locator(`[data-testid="reject-${toolCallId}"]`);
    await rejectBtn.click();
  }

  /**
   * Get risk badge by level
   */
  getRiskBadge(level: string): Locator {
    return this.page.locator(`[data-testid="risk-badge-${level}"]`);
  }

  /**
   * Check if streaming indicator is visible
   */
  async isStreaming(): Promise<boolean> {
    const indicator = this.page.locator('[data-testid="streaming-indicator"]');
    return indicator.isVisible();
  }

  /**
   * Wait for streaming to complete
   */
  async waitForStreamingComplete() {
    const indicator = this.page.locator('[data-testid="streaming-indicator"]');
    await indicator.waitFor({ state: 'hidden', timeout: 30000 });
  }

  /**
   * Get all visible message bubbles
   */
  async getMessages(): Promise<{ role: string; content: string }[]> {
    const bubbles = this.page.locator('[data-testid^="message-bubble-"]');
    const count = await bubbles.count();
    const messages: { role: string; content: string }[] = [];

    for (let i = 0; i < count; i++) {
      const bubble = bubbles.nth(i);
      const testId = await bubble.getAttribute('data-testid');
      const role = testId?.replace('message-bubble-', '') || 'unknown';
      const content = await bubble.textContent() || '';
      messages.push({ role, content });
    }

    return messages;
  }

  /**
   * Toggle a task in predictive demo
   */
  async toggleTask(taskId: string) {
    const task = this.page.locator(`[data-testid="task-${taskId}"]`);
    const checkbox = task.locator('input[type="checkbox"]');
    await checkbox.click();
  }
}

/**
 * Extended test fixture with AG-UI page object
 */
export const test = base.extend<{ agUiPage: AGUITestPage }>({
  agUiPage: async ({ page }, use) => {
    const agUiPage = new AGUITestPage(page);
    await agUiPage.goto();
    await use(agUiPage);
  },
});

export { expect } from '@playwright/test';
