---
document_id: QP-PAY-003
title: Payment Processing Guidelines
category: payments
---
# Payment Processing Guidelines

QueryPilot Demo Store models payment attempts using synthetic records only. It never
stores card numbers, bank credentials, or real payment-provider tokens.

## Failed payments and retries

A failed payment attempt collects no money and must not count as revenue. The order
remains pending while the fictional customer reviews the payment method. Some completed
or refunded orders have a failed attempt followed by one successful retry. Retrying does
not create another order or duplicate its line-item revenue.

## Successful settlement

Supported payment methods are card, bank_transfer, and wallet. Completed and refunded
orders each have exactly one successful payment matching the order total. A partial
unique index prevents a second successful payment for the same order. Pending orders
have no successful payment; cancelled orders in this fixture have no payment records.

## Payment amounts versus revenue

Payment reports group attempts by successful or failed status and use the UTC payment
date. Failed amounts are attempted charges, not cash received. Successful payment totals
include payments that were later refunded. Net settled cash subtracts actual refunds;
completed-order revenue instead filters current order status. Do not mix these definitions.
