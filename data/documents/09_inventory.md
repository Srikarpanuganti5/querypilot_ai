---
document_id: QP-INV-009
title: Inventory Management Policy
category: inventory
---
# Inventory Management Policy

QueryPilot Demo Store keeps a synthetic current stock snapshot for catalog demonstrations.
It does not operate a real warehouse or purchase inventory from external suppliers.

## Stock quantity meaning

Stock quantity is a nonnegative integer stored on each product. It represents an
illustrative current snapshot, not the number of units sold or a reservation balance.
The seed script does not decrement stock as it generates historical order items.
An order's sold quantity is recorded separately on its historical item rows.

## Replenishment review

The fictional warehouse reviews products with fewer than ten units for possible reorder.
This is a proposed operational threshold, not a process implemented in the database.
There are no supplier, purchase-order, inbound delivery, or restock event tables.
Analysts must not infer a supplier lead time from the stock snapshot.

## Returns and stock reconciliation

Approving a refund does not automatically increase the stored stock quantity. The current
fixture has no return inspection or inventory movement ledger. A later inventory workflow
would need explicit events and transactions; today's analytics cannot reconstruct a
historical stock balance or prove a returned product was resold.
