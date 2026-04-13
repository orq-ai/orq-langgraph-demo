# Customer Service Playbook

**Version:** 2025.1
**Audience:** Customer support agents handling inbound customer chat, email, and phone tickets.
**Purpose:** Give agents a consistent decision tree and scripted responses for the most common customer complaints so every customer receives a fair, fast resolution.

This playbook sits on top of three other documents that agents must be familiar with: the Refund and SLA Policy (the rules), the Delivery Operations Handbook (the flow), and the Allergen Labeling Policy (the facts). When a rule and this playbook disagree, the rule wins — this document describes the *conversation*, not the *policy*.

---

## §1. First response principles

- **Acknowledge quickly.** First response within 60 seconds on chat, 15 minutes on email.
- **Read the order first.** Pull up the order ID, SLA tier, delivery time, and any photo evidence before you type your first sentence. Nothing undermines a customer faster than asking them to repeat something the app already knows.
- **Name the issue.** Open with a sentence that tells the customer you understand what happened: "I can see your order was delivered 78 minutes after placement — that's well past our 60-minute threshold for a Standard delivery." Customers calm down the moment they feel heard.
- **Explain the resolution, then apply it.** State what you're going to do *before* you do it. "Because of the delay, I'm going to refund the delivery fee and add €5 in platform credit to your account. That will take effect within 2 minutes."
- **Document every decision.** Every refund has a reason code; every escalation has a summary. Future agents rely on these when the same customer comes back.

---

## §2. Scripted responses for common complaints

Use these as starting points, not verbatim responses. Adapt to the customer's tone.

### Late delivery

> "I can see your order arrived [X] minutes past our target time. I'm sorry about that — our target for a Standard order is 35 minutes and the late threshold is 60 minutes. Since your order was [X] minutes late, you're entitled to a [tier] refund under our Refund and SLA Policy. I'm applying that now. You'll see the credit in your app within a few minutes and a refund on your original payment method within 3-5 business days."

### Missing item

> "Thanks for letting me know. I can see [Item] was on your original order but you're saying it wasn't in the bag when you received it. I'm refunding the price of that item now, and I've opened an investigation with the restaurant. If you'd like a replacement, I can send a new order at no extra cost — would that work for you?"

### Wrong item

> "Sorry about that. I can see you ordered [X] and received [Y]. I'm refunding the full price of [X] now, and I'd be happy to send the correct item as a replacement at no charge. The restaurant can have it to you in about [estimated time]. Would you like me to do that?"

### Damaged / spilled order

> "That's really frustrating — thank you for the photo. Based on what I can see, [the lid seems to have come off in transit / the bag contents have been damaged]. I'm processing a full refund for the whole order now, and I've flagged this to our operations team so we can investigate. Refund will show up on your payment method within 3-5 business days."

### Allergen / food-safety concern (see §5 below for escalation)

> "Thank you for telling me — I take this very seriously. Can you tell me specifically what happened and how you're feeling now? I want to make sure we handle this correctly and, more importantly, that you're okay."

**Do not promise a refund, a replacement, or a specific medical outcome at this stage.** Route the ticket to the P1 Food Safety flow immediately. See §5.

### "I didn't like the food"

> "I'm sorry to hear that. Unfortunately, personal taste isn't something our refund policy covers, so I'm not able to refund the order just for that. If there was something specific wrong — a missing item, a wrong dish, or the food was damaged or cold — please let me know and I'll look into it."

Do not escalate subjective taste complaints unless the customer provides new information that qualifies under a policy category.

---

## §3. Decision tree — when to refund

```
Did the customer receive the order?
├── No (not delivered / left somewhere unsafe)
│   └── Is the order > 60 min past target (Standard) / 45 min (Priority)?
│       ├── Yes → Refund under late-delivery tier (Refund and SLA Policy §3)
│       └── No → Offer a welfare check with dispatch, then re-deliver if possible
│
└── Yes
    ├── Is the seal broken?                   → Full refund (Refund §2)
    ├── Does photo show damage?                → Full refund (Refund §6)
    ├── Is an item missing?                    → Item refund (Refund §4)
    ├── Is an item wrong?                      → Item refund + replacement offer (Refund §5)
    ├── Is the customer reporting illness?     → ESCALATE to P1 Food Safety (§5 below)
    ├── Is the customer reporting an allergen
    │   reaction?                              → ESCALATE to P1 Food Safety (§5 below)
    ├── Is the order > late threshold?         → Late-delivery tier (Refund §3)
    └── Is the complaint about taste alone?    → No refund (Refund §7)
```

---

## §4. Escalation ladder

Every agent has a €15 discretionary credit budget per customer per month. Beyond that, escalate.

| Level | Who handles it | Authority |
|---|---|---|
| L1 — First-line agent | The agent who answered the ticket | Refunds per Refund and SLA Policy, up to €15 discretionary credit |
| L2 — Senior agent | Senior agent queue | Up to €50 discretionary credit, manual override of a refund decision |
| L3 — Operations team | P2 queue, 24-hour SLA | Full override authority, restaurant disputes, driver disputes |
| L4 — Food Safety team | P1 queue, 2-hour SLA | Food safety incidents, Food Safety Incident Reports (FSIRs) |

### When to escalate to L2

- The customer is unhappy with an L1 decision and asks to speak to a supervisor.
- The refund amount under policy exceeds €15.
- The complaint involves a repeat issue (same customer, same restaurant, same problem) and needs a pattern-level review.

### When to escalate to L3

- A partner restaurant dispute needs resolving (restaurant disputes a refund the agent issued).
- A driver has been flagged 3+ times in 30 days and the agent is handling one of those complaints.
- The customer threatens legal action or mentions media/regulatory involvement.

### When to escalate to L4

- Any mention of illness, allergen reaction, foreign object, or contamination. Even if the customer is unsure — escalate. See §5.

---

## §5. Food safety incidents (P1)

A P1 food-safety incident is any customer complaint that mentions:

- Symptoms of illness after eating the order (nausea, vomiting, diarrhea, rash)
- An allergen reaction
- A foreign object in the food (plastic, metal, hair, insect)
- The order being at the wrong temperature in a way that could indicate spoilage

### Handling flow

1. **Acknowledge the customer's wellbeing first.** "I'm so sorry you're feeling unwell. Are you okay right now? Do you need medical attention?" If they need urgent help, advise them to call their local emergency number.
2. **Do not discuss the refund amount yet.** The priority is incident containment.
3. **Collect facts.** Ask: which dish, which restaurant, when they ate, what symptoms started, whether anyone else in the household is affected, and whether they still have the packaging.
4. **Open a Food Safety Incident Report (FSIR).** Use the support tool's P1 Food Safety template. Include the order ID, dish, restaurant ID, customer's description, and any photo.
5. **Route to the Food Safety team.** P1 tickets have a 2-hour SLA. The Food Safety team will contact the partner restaurant, review temperature logs (see Food Safety and Hygiene Policy §1), and coordinate the customer's refund and any further goodwill.
6. **Apply an immediate courtesy refund.** Issue a full order refund as a goodwill gesture without waiting for the FSIR outcome. The Food Safety team will reconcile liability afterwards.
7. **Follow up.** Re-contact the customer within 24 hours via the FSIR update channel.

### What NOT to do

- **Do not** admit liability on behalf of the delivery service, the restaurant, or the driver. Use neutral language: "I've opened a food safety investigation" rather than "I agree this is the restaurant's fault."
- **Do not** advise the customer on medical treatment.
- **Do not** close the ticket until the Food Safety team has reviewed the FSIR.

---

## §6. Tone and de-escalation

Angry customers are usually angry about something real. Most of the time, the fastest path to calm is acknowledging the problem and moving to the fix.

- **Acknowledge the feeling**, not just the fact: "That's incredibly frustrating, especially when you were expecting dinner an hour ago."
- **Avoid policy language up front**: Don't start with "According to our Refund and SLA Policy §3…" — customers hear that as a no before they hear the yes. Apply the policy but describe it in plain terms.
- **Own the outcome**: "Here's what I'm going to do" is stronger than "Here's what I can do."
- **Apologize without groveling**: One sincere apology is enough. Repeating it three times makes the customer feel you're stalling.
- **Stay calm if the customer swears or escalates**: Their anger is almost never about you personally. Stick to the decision tree.
- **Close with a concrete next step**: "You should see the refund in 3-5 business days. If you don't, reply to this conversation and I'll chase it up." Always give the customer an out for follow-up.

---

## §7. Keeping up to date

This playbook is reviewed quarterly. When a policy referenced here changes, this document is updated within 7 days. Agents should refresh their memory of the escalation ladder once a month.

Questions about this playbook should be directed to `support-training@deliveryservice.internal`.
