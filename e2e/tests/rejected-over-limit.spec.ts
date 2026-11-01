import { expect, test } from "@playwright/test";
import { InvoiceAppPage } from "../pages/invoice-app.page";

test("a manager is refused above 50000 and the invoice stays pending", async ({ page }) => {
  const app = new InvoiceAppPage(page);
  await app.signIn("demo.manager", "ChangeMe123!");

  const row = await app.createInvoice("Over Limit District", "50000.01");
  const invoiceId = (await row.getByRole("cell").nth(0).innerText()).trim();
  await app.submit(row);
  await app.openApprovals();
  await app.approve(invoiceId);

  await expect(app.decisionAlert()).toContainText("50,000.00");
  await expect(app.decisionAlert()).toContainText("left unchanged");

  await app.openInvoices();
  await expect(row.getByRole("cell").nth(2)).toHaveText("$50,000.01");
  await expect(row.getByRole("cell").nth(3)).toHaveText("Pending Approval");
});
