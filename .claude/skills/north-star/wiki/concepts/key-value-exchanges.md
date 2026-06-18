---
title: Key Value Exchanges — Where Customers Derive Value
type: concept
schema_version: 1
sources:
  - definitions/definition-p038-l0892-key-value-exchange.md
  - principles/principle-p038-l0892-isolate-three-to-six-value-exchanges.md
  - concepts/concept-p038-l0900-value-exchanges-outside-product.md
related:
  - wiki/concepts/north-star-metric.md
  - wiki/concepts/two-categories-of-trouble.md
  - wiki/concepts/games.md
playbook_pages: [38]
tier: 1
confidence: high
confidence_derivation: "Anchor definition 3/3; principle 3/3; supporting concept 4/4 → high."
curator_status: approved
verified: true
created: 2026-05-26
updated: 2026-05-26
---

# Key Value Exchanges — Where Customers Derive Value

## TL;DR
A key value exchange is one of a handful — typically three to six — essential actions where customers derive value from the product. Value exchanges show the product's true essence and should be reflected in the NSM where possible. Critically, they often happen OUTSIDE the product itself (e.g., the concert-goer arriving at their seat is a key value exchange for a ticketing app); don't exclude these stories just because they don't occur in the software.

## Decision rule
- Isolate three to six key value exchanges for the product [principle-p038-l0892-isolate-three-to-six-value-exchanges].
- An action qualifies as a key value exchange iff it is essential AND the customer derives value from it.
- Include value exchanges that happen OUTSIDE the product surface — these are often the most strategically important [concept-p038-l0900-value-exchanges-outside-product].
- Reflect the key value exchanges in the NSM where possible.

## Detail
Canonical definition: "Even with complex products, you can typically isolate a handful of three to six essential actions or events where customers derive value from the product. These key value exchanges demonstrate the true essence and intent of your product" [definition-p038-l0892-key-value-exchange].

The numeric guideline is stated as a rule: "Even with complex products, you can typically isolate a handful of three to six essential actions or events where customers derive value from the product" [principle-p038-l0892-isolate-three-to-six-value-exchanges]. Three is a floor, six is a ceiling — fewer than three usually means the team is conflating value exchanges; more than six usually means the team is listing features instead.

**The outside-the-product extension** is the load-bearing clarification: "For many products, some key value exchanges happen outside the actual product — for example, the concert-goer arriving at their chosen seat is a key value exchange for a ticketing app. Don't exclude these important stories just because they don't occur within the product itself" [concept-p038-l0900-value-exchanges-outside-product].

This matters because product analytics tooling biases teams toward in-app events. A ticketing app whose value-exchange list is limited to "purchase complete," "ticket emailed," "ticket scanned at venue" misses the actual moment of customer value — being at the seat for the show. A grocery-delivery app's value exchange is the customer eating the groceries, not the click that submits the order. Building the NSM around the in-app event when the actual value exchange is downstream produces metrics that move while customer outcomes stagnate.

Key value exchanges are one of the three "shared understanding" tools the playbook prescribes for teams stuck disagreeing about the NSM — alongside [Beliefs](beliefs.md) and [Product Vision](product-vision.md). See [Two Categories of Trouble](two-categories-of-trouble.md).

## yaml-rules
```yaml
key_value_exchange:
  count_range: [3, 6]
  qualifies_if:
    - is_essential
    - customer_derives_value
  may_occur_outside_product: true
  include_in_nsm_design: when_possible
common_failure_modes:
  - listing_in_app_events_only
  - confusing_features_with_value_exchanges
  - conflating_multiple_exchanges_into_one
identifying_questions:
  - what_does_the_customer_value
  - where_does_the_value_actually_get_delivered
  - is_the_value_inside_or_outside_the_product
related_to_shared_understanding_tools:
  - beliefs
  - product_vision
  - key_value_exchanges
```

## Related
- [North Star Metric](north-star-metric.md)
- [Two Categories of Trouble](two-categories-of-trouble.md)
- [The Game](games.md)
