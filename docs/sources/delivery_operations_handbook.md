# Delivery Operations Handbook

**Version:** 2025.1
**Audience:** Delivery drivers, operations analysts, dispatch team, and customer support agents.
**Purpose:** Describe the end-to-end delivery flow, SLA tiers, pickup and dropoff protocols, and dispute handling for everyone operating on the delivery service platform.

---

## §1. The delivery flow

Every order passes through the same six stages from placement to delivery. Understanding the flow is the foundation for every other procedure in this handbook.

1. **Customer places order** — the customer confirms items and delivery address in the app. The order enters the dispatch queue.
2. **Dispatch assignment** — the dispatch system assigns the order to the nearest available driver with a clear path to the restaurant. Assignment happens within 90 seconds of placement on average.
3. **Driver en route to restaurant** — the driver accepts the order and travels to the partner restaurant. The customer sees a "Driver en route" status.
4. **Pickup handover** — the driver collects the sealed order from the restaurant, verifies the order ID on the receipt, and marks pickup complete in the driver app.
5. **Driver en route to customer** — the driver follows the app's suggested route to the customer's address. The customer sees the driver's position on the live map.
6. **Dropoff** — the driver delivers the order to the customer according to the selected dropoff mode (see §3).

Total target time from placement to dropoff: **under 35 minutes** in urban areas during non-peak hours.

---

## §2. SLA tiers

The delivery service offers three SLA tiers. Every order has a **target delivery time** (the promise made to the customer at checkout) and a **late threshold** (the point at which refund compensation kicks in).

### Standard (default)

- **Target:** 35 minutes from order placement to dropoff.
- **Late threshold:** 60 minutes.
- **Refund tier if late:** See Refund and SLA Policy §3.
- **Applies to:** Every order without explicit upgrade.

### Priority

- **Target:** 25 minutes.
- **Late threshold:** 45 minutes.
- **Refund tier if late:** Higher compensation — see Refund and SLA Policy §3.
- **Applies to:** Orders where the customer paid a Priority surcharge at checkout.

### Scheduled

- **Target:** Delivered within a 10-minute window around the customer's chosen time.
- **Late threshold:** 15 minutes after the window closes.
- **Refund tier if late:** Full delivery fee refund.
- **Applies to:** Orders placed in advance with a scheduled delivery time.

---

## §3. Dropoff modes

Drivers must select the correct dropoff mode based on the customer's instructions in the app.

### Hand-to-customer

- The driver must hand the order directly to the customer and verify the customer's name or order ID.
- If the customer is not at the door, the driver waits up to **5 minutes**, then attempts to call the customer.
- If the customer does not answer after 3 call attempts, the driver may wait an additional 5 minutes at their discretion, then follow the non-responsive customer protocol below.

### Contactless

- The driver leaves the order at the customer's door without direct contact, takes a timestamped photo of the delivery placement, and uploads it to the app as proof of delivery.
- The driver must then immediately mark the order as delivered and leave the premises.
- If the customer's chosen location is unclear (e.g., "front porch" but no visible porch), the driver must call the customer for clarification **before** leaving the order.

### Leave with concierge / reception

- The driver hands the order to the concierge or receptionist at the address, records their name in the app, and takes a timestamped handover photo.

### Non-responsive customer protocol

If a customer does not answer the door or the phone after the maximum wait (10 minutes total for hand-to-customer; 3 call attempts for contactless):

1. The driver contactless-delivers the order at a safe location if possible and uploads a photo.
2. If contactless delivery is not safe (street drop, no safe spot), the driver marks the order as "customer unreachable" and returns the order to the dispatch center.
3. The customer is charged the full amount; no refund is due unless they dispute via the complaint flow (see Customer Service Playbook §3).

---

## §4. Pickup handover protocol

At the partner restaurant:

1. Greet the restaurant staff and state the order ID.
2. Receive the sealed order. **Never** accept an unsealed or broken-seal order — request a reseal.
3. Verify the bag feels hot (for hot items) or cool (for cold items). If the temperature seems wrong, notify operations via the driver app's "Temperature concern" button and wait for instructions before departing.
4. Confirm pickup in the driver app within 60 seconds of receiving the bag.
5. Leave promptly — do not loiter or open the bag en route. The seal is the customer's guarantee of non-tampering.

See Food Safety and Hygiene Policy §1 for the formal temperature bands. If a temperature concern escalates, operations may instruct the driver to decline the order entirely.

---

## §5. Driver performance

Drivers are evaluated on three metrics:

- **On-time rate:** Percentage of orders delivered by the target time (Standard: 35 min; Priority: 25 min; Scheduled: within the 10-min window). Target: ≥ 92%.
- **Customer rating:** 5-star rating average across the driver's last 500 orders. Target: ≥ 4.6.
- **Acceptance rate:** Percentage of dispatched orders accepted. Target: ≥ 75%. Drivers may decline an order without penalty if the restaurant is >15 minutes away or if the driver is at the end of a shift.

Drivers whose metrics drop below target receive a coaching session. Three consecutive months below target trigger a performance review.

---

## §6. Disputes and incidents

### Missing item

- Customer reports a missing item after delivery.
- Agent opens a missing-item claim in the support tool.
- If the order photo or pickup receipt confirms the item was in the bag at pickup, the claim goes to the partner restaurant.
- If not, the claim is refunded to the customer at the item price. See Refund and SLA Policy §4.

### Damaged order

- Customer reports the order arrived damaged (spilled, crushed, contaminated).
- Agent requests a photo from the customer.
- If the damage is verifiable, the customer receives a full refund. The restaurant may dispute the driver's handling if the photo shows transit damage.

### Wrong item

- Customer reports receiving a different dish than ordered.
- Agent verifies the app order ID against the photo.
- Wrong-item claims are always refunded to the customer and charged back to the restaurant.

### Late delivery

- Automated: the system opens a late-delivery claim when the target time is exceeded by more than the late threshold (Standard: 60 min; Priority: 45 min).
- Refund is applied automatically per Refund and SLA Policy §3.

### Food safety incident

- Any customer complaint mentioning illness, contamination, or allergen exposure is a P1. See Food Safety and Hygiene Policy §6 and Customer Service Playbook §5 for the handling flow.

---

## §7. Communication

- All operational chatter between drivers and dispatch happens via the driver app's built-in chat.
- Drivers **must not** share their personal phone number with customers. All customer calls go through the app's masked-number relay.
- Drivers **must not** discuss pricing, complaints, or refunds with customers — redirect them to the support chat in the app.

Questions about this handbook should be directed to `ops@deliveryservice.internal`.
