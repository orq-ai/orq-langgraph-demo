# Refund and SLA Policy

**Version:** 2025.1
**Scope:** All customer-facing refund decisions and SLA commitments for the delivery service.
**Purpose:** Define clear, consistent rules for when a customer is eligible for a refund, how much, and who absorbs the cost. Support agents must use this document as the single source of truth when handling refund requests — no ad-hoc discretion.

This policy is read by both customer-support agents (to decide refund cases) and operations analysts (to understand how late-delivery compensation affects per-order economics).

---

## §1. Principles

The delivery service refund policy is designed around three principles:

1. **Customer first**: When a customer has a legitimate grievance (late, wrong, missing, damaged, unsafe), they receive a refund quickly. Disputes between the restaurant and the driver are resolved internally afterwards — **never** at the customer's expense.
2. **Tiered compensation**: Late deliveries are compensated at increasing rates based on how late the order is. The customer does not forfeit the order because it's late — they may keep it and still receive compensation.
3. **Transparency**: Every refund is logged with a reason code and visible to the customer in the app's order history.

---

## §2. Refund categories

Refunds fall into six categories. The category determines the compensation tier and who absorbs the cost.

| Category | Trigger | Typical compensation | Cost absorbed by |
|---|---|---|---|
| Late delivery | Target time exceeded by > late threshold | Sliding scale (see §3) | Delivery service |
| Missing item | Customer reports an item missing from the bag | Item price refunded | Restaurant (usually) or delivery service |
| Wrong item | Customer receives a different dish than ordered | Full item refund + replacement offer | Restaurant |
| Damaged order | Order arrives spilled, crushed, or contaminated | Full order refund | Driver / delivery service |
| Broken seal | Tamper-evident seal broken on arrival | Full order refund + P1 food-safety flag | Restaurant or driver (investigated) |
| Food safety | Customer reports illness, allergen reaction, or foreign object | Full refund + Food Safety Incident Report | Delivery service (pending investigation) |

---

## §3. Late-delivery compensation tiers

A late delivery is compensated when the order arrives after the **late threshold** for its SLA tier. The compensation increases with lateness.

### Standard SLA orders (target: 35 min, late threshold: 60 min)

| How late | Compensation |
|---|---|
| 60 min to 75 min | 20% of delivery fee |
| 75 min to 90 min | 100% of delivery fee |
| 90 min to 120 min | 100% of delivery fee + €5 credit |
| Over 120 min | 100% of delivery fee + 20% of order total as credit |

### Priority SLA orders (target: 25 min, late threshold: 45 min)

| How late | Compensation |
|---|---|
| 45 min to 60 min | 50% of delivery fee + full priority surcharge refund |
| 60 min to 75 min | 100% of delivery fee + full priority surcharge refund |
| 75 min to 90 min | 100% of delivery fee + full priority surcharge refund + €5 credit |
| Over 90 min | 100% of delivery fee + full priority surcharge refund + 25% of order total as credit |

### Scheduled SLA orders (target: customer's chosen 10-min window, late threshold: 15 min after window closes)

- 15 min to 30 min after window: 100% of delivery fee
- Over 30 min after window: 100% of delivery fee + 20% of order total as credit

### Rule of thumb

When in doubt, the support agent should err on the side of the higher tier. A €5 credit that over-compensates a customer by €2 is cheaper than losing their trust.

---

## §4. Missing-item refunds

### Eligibility

- The customer reports the missing item **within 30 minutes** of delivery via the in-app support chat.
- The missing item must be on the original order receipt.
- The customer may be asked to provide a photo of what they received if the claim is ambiguous.

### Compensation

- **Full item price** is refunded to the customer's original payment method.
- No delivery-fee refund is issued for missing-item claims unless the missing item represents more than 50% of the order total — in which case the full delivery fee is also refunded.

### Cost attribution

- If the pickup photo (taken by the driver at handover) shows the item was in the bag: the restaurant absorbs the cost.
- If no pickup photo exists or the photo is inconclusive: the delivery service absorbs the cost.

---

## §5. Wrong-item refunds

### Eligibility

- The customer reports the wrong item **within 45 minutes** of delivery.
- The customer provides a photo of the delivered item showing the discrepancy.
- The wrong item must differ from the order in a material way — e.g., Margherita instead of Pepperoni Pizza, or vegetarian instead of meat.

### Compensation

- **Full item refund** to the customer's original payment method.
- The support agent may offer a replacement delivery at no extra cost if the customer requests it and the restaurant is still open. Replacement delivery uses a new order ID.

### Cost attribution

Always charged back to the partner restaurant. Wrong-item claims are a restaurant kitchen error.

---

## §6. Damaged order refunds

### Eligibility

- The customer reports damage (spilled, crushed, contaminated) **within 30 minutes** of delivery.
- A photo of the damage is required.

### Compensation

- **Full order refund** (all items + delivery fee) to the customer's original payment method.

### Cost attribution

- If the photo shows spillage or damage consistent with rough handling in transit: the driver is flagged and the delivery service absorbs the cost. Three flags in 30 days triggers a driver review.
- If the photo shows a kitchen error (e.g., a rupture at the seal): the restaurant absorbs the cost.

---

## §7. Non-refund scenarios

The following situations do **not** qualify for a refund:

- The customer did not like the taste of a dish (subjective preference is not a refund trigger).
- The customer reports damage more than 30 minutes after delivery and provides no photo.
- The customer requested a substitution and the restaurant complied with the substitution as requested.
- The customer was non-responsive at delivery (see Delivery Operations Handbook §3) and the order was contactless-delivered as a fallback — unless the customer disputes the delivery location.
- The customer reports a "late" delivery that is actually within the target time. Agents must check the order's actual target time, not the customer's subjective expectation.

---

## §8. Credit vs cash refund

- **Cash refund** (to original payment method) is the default for all refund categories above.
- **Platform credit** may be offered in place of cash if the customer prefers, or as an **additional** goodwill gesture on top of a cash refund (e.g., in the late-delivery tiers where credit stacks with the fee refund).
- Credit expires after 12 months.

---

## §9. Escalation

If a customer disputes a refund decision:

1. The first-line agent must document the reason code and the customer's specific objection.
2. If the customer is unhappy with a Standard-tier decision, escalate to a senior agent who can apply discretionary credit up to €15.
3. If the customer is still unhappy, escalate to the operations team via the P2 queue. Ops will review within 24 hours and respond to the customer directly.

See Customer Service Playbook §4 for the full escalation decision tree.
