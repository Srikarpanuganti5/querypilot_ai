---
document_id: QP-FAQ-010
title: Business Analytics Frequently Asked Questions
category: faq
---
# Business Analytics Frequently Asked Questions

QueryPilot Demo Store documentation and commerce records are fictional portfolio assets.
This FAQ explains interpretation limits rather than generating live business answers.

## Dataset dates and reproducibility

The reference fixture contains 500 customers, 100 products, 3000 orders, and 6000 item
rows. Generation uses an explicit reference date and fixed random seed. Orders cover the
previous twelve calendar months in UTC, excluding the reference date. A rolling year
can span thirteen calendar month buckets because its first and last months are partial.

## Revenue and refund definitions

Completed-order revenue sums current completed orders, excluding pending, cancelled,
and fully refunded orders. Successful payments measure gross settled cash; net settled
cash subtracts actual refunds. These are different metrics and can have different dates.
Never subtract refunds again from an already filtered completed-order revenue total.

## What the application can answer

The five SQL tools provide approved commerce aggregates. Document search retrieves local
policy passages and citations; it does not generate an AI answer or execute the text.
Shipment tracking, support tickets, partial returns, fraud decisions, and historical
inventory balances are unavailable. No external search, language model, or live merchant
system is connected during Day 5.
