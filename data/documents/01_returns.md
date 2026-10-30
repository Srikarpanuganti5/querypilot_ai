---
document_id: QP-RET-001
title: Returns and Refund Policy
category: refunds
---
# Returns and Refund Policy

QueryPilot Demo Store is a fictional merchant. This policy describes synthetic business
rules for the portfolio dataset, not a real consumer contract.

## Product return window

Customers may request a return within 30 calendar days of delivery. Returned products
must be unused, complete, and in their original packaging. A support case records the
synthetic order ID and reason. Delivery events are illustrative and are not stored in
the Day 3 database; analysts cannot calculate return eligibility from those tables alone.

## Full refund processing

The demonstration supports full-order refunds only. Support confirms a successful payment
before approving the return. The refund amount equals the original settled payment;
total refunds must never exceed that payment. The refund record references the payment,
records a reason and UTC refund date, and the order becomes refunded. Partial item returns
and partial refunds are outside the current dataset.

## Refund reporting

Completed-order revenue excludes fully refunded orders. Do not subtract refunds again
from that metric. Refund analytics use the refund date, which can fall in a later month
than the order. Category refund amounts are allocated using each original line's share
of the order value; category counts are not additive across categories.
