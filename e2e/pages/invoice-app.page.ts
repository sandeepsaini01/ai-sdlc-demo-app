import { expect, type Locator, type Page } from "@playwright/test";

export class InvoiceAppPage {
  constructor(private readonly page: Page) {}

  async signIn(username: string, password: string): Promise<void> {
    await this.page.goto("/");
    await this.page.getByLabel("Username").fill(username);
    await this.page.getByLabel("Password").fill(password);
    await this.page.getByRole("button", { name: "Sign in" }).click();
    await expect(this.page.getByRole("button", { name: "Sign out" })).toBeVisible();
  }

  async createInvoice(customer: string, amount: string): Promise<Locator> {
    await this.page.getByLabel("Customer name").fill(customer);
    await this.page.getByLabel("Amount").fill(amount);
    await this.page.getByRole("button", { name: "Create invoice" }).click();
    const row = this.page.getByRole("row").filter({ hasText: customer });
    await expect(row).toBeVisible();
    return row;
  }

  async submit(row: Locator): Promise<void> {
    await row.getByRole("button", { name: /Submit invoice/ }).click();
    await expect(row.getByRole("cell").nth(3)).toHaveText("Pending Approval");
  }

  async openApprovals(): Promise<void> {
    await this.page.getByRole("tab", { name: "Approvals" }).click();
  }

  async openInvoices(): Promise<void> {
    await this.page.getByRole("tab", { name: "Invoices" }).click();
  }

  async approve(invoiceId: string): Promise<void> {
    await this.page.getByRole("button", { name: `Approve invoice ${invoiceId}` }).click();
  }

  decisionAlert(): Locator {
    return this.page.getByRole("alert");
  }
}
