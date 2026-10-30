---
document_id: QP-CAN-004
title: Order Cancellation Rules
category: cancellations
---
# Order Cancellation Rules

QueryPilot Demo Store uses four order statuses: pending, completed, cancelled, and refunded.
The following fictional workflow explains those statuses without adding new database fields.

## When customers can cancel

Customers may request cancellation while an order is pending and has no successful
payment. Support checks the order ID and settlement state before recording a decision.
Cancellation ends the unfulfilled order; it does not create revenue. The current dataset's
cancelled orders have no payment records and remain excluded from revenue analytics.

## After a completed payment

A completed order is not converted to cancelled. If a paid order must be reversed,
support uses the full-order return and refund process. A refunded order retains its
successful payment and adds a linked refund record, preserving the accounting trail.
This dataset does not model a separate payment authorization or void stage.

## Cancellation reporting

Customer order counts may include cancelled and pending orders, but completed revenue
includes neither. Cancellation timestamps and reasons are not separate schema columns,
so current order statuses cannot establish the historical moment a cancellation occurred.
Search retrieves policy passages; it cannot cancel or modify an order.
