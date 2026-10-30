---
document_id: QP-CAT-005
title: Product Categories and Catalog Rules
category: products
---
# Product Categories and Catalog Rules

The fictional QueryPilot Demo Store catalog contains 100 synthetic products. Product
labels identify demonstration records and do not refer to real branded merchandise.

## Approved catalog categories

The five product categories are Electronics, Home, Sports, Outdoors, and Office.
Each product has one category, a positive USD catalog price, and a nonnegative stock
snapshot. A product belongs to one category even when several categories appear in
the same customer order.

## Historical product prices

Order items preserve the unit price charged at purchase. Analysts calculate product
revenue from quantity multiplied by that historical unit price, not today's product
catalog price. Synthetic promotions can make the unit price lower than the catalog
price. Updating a catalog price must not change existing order totals.

## Category aggregation

Product revenue uses completed orders only. Category order counts are distinct within
each category; a mixed-category order can appear in several category counts. Product
revenue ties are ordered by ascending product ID. Product stock is not a sales total,
and category refund allocations follow original line values.
