# Prior art — why Thaw is different

Say this early, before anyone asks.

| System | What it does | What it doesn't |
|---|---|---|
| **Razorpay Agent Studio** (Mar 2026) | Lets you build agents on Razorpay data/actions | Doesn't decide which checkout setting is worth re-testing, or prove it safely on live traffic |
| **Razorpay Optimizer** | Picks the gateway *behind* a payment for higher auth rates | Works below checkout; doesn't touch what the customer *sees* (`config.display.sequence`) |
| **Adyen experimentation** | A/B tests on the checkout layer | A human starts and stops each test; no autonomous feasibility/spending-cap/brake loop |
| **Standard canary release** | Ship to 5% of traffic, watch dashboards, roll back | Assumes rollback is free. A failed checkout is a lost order — it isn't |
| **Thaw** | Notices a frozen setting moved, decides *which* fix is worth running, proves it under a rupee cap with an emergency brake, and remembers the result | Doesn't execute on live money (test mode + simulator); effects inflated for the demo |

## The one-line separations
- Agent Studio is the *platform*; Thaw is a *product built on the idea*.
- Optimizer optimizes the *rail*; Thaw optimizes the *choice architecture the buyer sees*.
- Adyen needs a *human operator*; Thaw runs the feasibility → cap → brake → ledger loop itself.
- A canary trusts *rollback*; Thaw caps *loss in rupees before the test starts*, because rollback here isn't free.

## The safety model is from clinical trials, not software releases
Being in the wrong group causes real harm (a lost customer), and you can't wait for
the study to finish to act. So: loss capped up front; asymmetric evidence (weak
evidence stops a test, strong evidence promotes one); an independent monitor that
outranks the agent.
