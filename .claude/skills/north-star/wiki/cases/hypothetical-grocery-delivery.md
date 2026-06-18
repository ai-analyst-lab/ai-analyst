---
title: Hypothetical Grocery Delivery Service — Monthly Items Received On Time
type: case
schema_version: 1
sources:
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0177-grocery-delivery-nsm-monthly-items.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0179-grocery-input-1-place-orders.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0180-grocery-input-2-orders-with-items.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0181-grocery-input-3-fulfilling-orders.md
  - raw/atoms/case-study-fragments/case-study-fragment-p008-l0182-grocery-input-4-delivering-on-time.md
related:
  - wiki/concepts/inputs.md
playbook_pages: [8]
case_id: case-hypothetical-grocery-delivery
company: Hypothetical grocery delivery service
game: transaction
industry: delivery
stage: not-applicable
nsm:
  statement: "Total monthly items received on time"
  grain: per-month-items
inputs:
  - place_lots_of_orders
  - orders_with_lots_of_items
  - fulfilling_lots_of_orders
  - delivering_on_time
evolution: []
outcome: hypothetical
tier: 1
confidence: medium
confidence_derivation: "All cited fragments curator-approved Tier 1. Per the source, this is an explicit hypothetical illustration ('let's say'), not a real company. Confidence-medium reflects pedagogical purpose, not external verification."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Hypothetical Grocery Delivery Service — Monthly Items Received On Time

## TL;DR
This is a **hypothetical worked example**, not a real company. The playbook proposes a grocery-delivery service with the NSM "total monthly items received on time" and decomposes it into four explicit inputs: drive customers to place lots of orders, encourage orders with lots of items, fulfill lots of orders, and deliver orders on time. Used to teach how to design an NSM that captures both demand and fulfillment quality in one metric.

## Story
The playbook uses a hypothetical grocery-delivery service as its first worked example of decomposing an NSM into inputs. The proposed NSM is "total monthly items received on time" [case-study-fragment-p008-l0177-grocery-delivery-nsm-monthly-items]. The metric is constructed deliberately to capture three things in one number: scale (monthly items), depth-of-basket (items, not just orders), and quality (received on time, not just dispatched).

The decomposition that follows is the case's teaching payload. The NSM resolves to four named inputs on the demand and supply sides of the marketplace:

1. **Driving customers to place lots of orders** [case-study-fragment-p008-l0179-grocery-input-1-place-orders] — the demand-frequency input.
2. **Encouraging orders with lots of items** [case-study-fragment-p008-l0180-grocery-input-2-orders-with-items] — the basket-size input.
3. **Fulfilling lots of orders** [case-study-fragment-p008-l0181-grocery-input-3-fulfilling-orders] — the supply-side capacity input.
4. **Delivering orders on time** [case-study-fragment-p008-l0182-grocery-input-4-delivering-on-time] — the last-mile quality input.

Because the example is hypothetical, the playbook does not detail squad assignments, evolution, or outcomes — those are reserved for the named-company cases. The point of this case is the input-decomposition shape: a marketplace-style NSM naturally splits into demand and supply inputs, with a quality gate on at least one of them.

## Why it works
The case is the cleanest pedagogical demonstration of how to construct an NSM that prevents "rate-vs-count" gaming. Counting orders alone rewards thin baskets; counting items alone rewards padded carts; counting deliveries alone ignores cancellations and late arrivals. Combining items × on-time forces the team to optimize the full unit of customer value at once. The four inputs cover the demand and supply faces of the marketplace, and each input is intervenable by a distinct team.

## What broke
The case is explicitly hypothetical — the playbook frames it with "for example, let's say." It does not name a real grocery-delivery company, does not specify a sub-input architecture, and does not document any outcome data. Confidence is medium because there is nothing to validate externally; the case stands or falls on whether the decomposition is pedagogically useful. Curators should never treat this case as evidence that any real grocery-delivery company uses this NSM construction.
