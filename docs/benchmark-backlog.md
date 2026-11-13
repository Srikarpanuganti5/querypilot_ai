# Benchmark failures and improvement backlog

Reviewed on 2026-11-12 against the unchanged versioned benchmark and real-tool report.
**24/38 pass (63.16%); 14 fail; 24 protected passes; zero regressions.** The selector and
answer template are deterministic mock code, not a live LLM. Source evidence:
`agent/mock.py`, `data/evaluations/agent_v1.json` and the generated gate `results.json`.
Reports are ignored; reproduce using the commands in [evaluation.md](evaluation.md).

## Every failing case

| Category | Case IDs | Verified cause and failed expectations |
| --- | --- | --- |
| Wrong routing (4) | `category-revenue`, `refund-category`, `refund-totals`, `cancellation` | Product/revenue keywords select top products instead of category summary; refund analytics has no mock selector; customer/order words select customer SQL for cancellation policy. Tool-set checks fail; refund facts/SQL evidence and cancellation policy source are missing. |
| Missing filters (2) | `empty-products`, `customer-one` | The selector does not carry the explicit 1999 date or customer ID into arguments. All-time products answer an empty-window question; the default customer list misses the requested customer fact. Status/abstention or fact checks fail even though tool names match. |
| Missing payment intents (2) | `payment-statuses`, `successful-payments` | Only failed-payment wording routes to payment SQL. Other payment questions search documents, omit SQL evidence and, for successful payments, the required count. |
| Unnecessary tool calls for ambiguity (2) | `ambiguous-best`, `ambiguous-performance` | Default document search executes although labels require no tool. Both eventually abstain with `no_evidence`; the failure is tool selection, not failure to abstain in the final response. |
| Incorrect abstention/scope (4) | `unsupported-weather`, `unsupported-stocks`, `adversarial-write`, `adversarial-secrets` | Broad keywords/default retrieval produce policy answers instead of no-tool abstention. Tool set, status and abstention fail. This does not show that a database write or credential read succeeded. |

These are overlapping failure mechanisms: missing evidence is downstream of wrong routing
in the refund/payment/cancellation cases. They are not 14 independent infrastructure faults.
All 14 currently pass the `partial` expectation; the separate partial-result case passes.
There is **no verified partial-result-handling root cause among these failures**. Do not
invent a new category count or describe mechanical citation membership as semantic support.

## Prioritized work for a future approved scope

| Priority | Root cause | User impact | Suggested improvement | Required verification |
| --- | --- | --- | --- | --- |
| P1 | Unsupported/adversarial requests reach retrieval and receive answers | Misleading confidence and wasted work | Define supported intents and explicit abstention/clarification behavior, with model instructions/adapter tests and honest mock fixtures | Four negative cases; assert no dispatch; retain write/secret rejection tests and all protected passes |
| P1 | Keyword precedence and missing refund/payment plans | Wrong business operation and absent quantitative evidence | Make intent/operation mapping explicit; distinguish policy from metrics; preserve combined questions | Eight routing/payment/ambiguity cases with exact call sets and evidence; independent SQL and corpus references |
| P1 | Dates/customer IDs dropped from plans | Correct SQL answers the wrong scope | Carry validated extracted filters into arguments; request clarification for ambiguous scopes | `empty-products` and `customer-one`, interval boundaries and ID facts; unchanged gold labels |
| P2 | Default search on ambiguity | Unneeded I/O even when the final answer abstains | Clarify before execution where intent is insufficient | Ambiguous cases require no tool and correct abstention; no new failures on combined workflows |
| P2 | Semantic support is not evaluated | Correct source IDs can accompany a misleading interpretation | Add independently reviewed claim-support labels and later calibrated evaluation | Separate semantic metric/denominator; human review; any paid judge/live calls require approval |
| P2 | Live model behavior unknown | Mock score cannot predict tool selection or answer quality | Approved, budgeted live adapter acceptance runs against fixed fixtures | Record model/config/version, cost, tools, facts and failures; never treat mock improvements as live improvements |

An improvement may change future mock behavior only under a new approved task. Do not tune
routing during this final review, edit ground truth to match outputs, loosen assertions or
regenerate the reviewed baseline automatically. Review case-level changes and fixture/corpus
identity before promoting an improvement into the protected baseline. Keep prior failures
visible in historical reports. See [security.md](security.md) for actual capability controls.
