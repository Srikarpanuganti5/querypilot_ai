---
document_id: QP-DSC-007
title: Discounts and Promotional Pricing
category: discounts
---
# Discounts and Promotional Pricing

QueryPilot Demo Store includes synthetic promotional pricing to demonstrate historical
purchase values. No live coupon engine, advertising service, or campaign account exists.

## Promotion rates

The demonstration generator chooses no discount, a five percent discount, or a ten
percent discount on each selected product line. Promotions do not stack. The adjusted
unit price is rounded to USD cents using Decimal half-even rounding before multiplying
by quantity. These rates explain the fixture and are not a checkout API.

## Order total calculation

An order total is the sum of quantity times stored unit price over all its order items.
There are no separate coupon, tax, shipping, or discount amount columns. Reapplying
a percentage discount to the stored unit price would double-count the promotion.
Cancelled and pending orders still retain their original quoted line totals.

## Refunding promotional orders

A full-order refund returns the actual successful payment amount, which already reflects
promotional prices. It does not refund the undiscounted catalog value. Historical item
prices remain unchanged so revenue and refund category allocations reconcile.
