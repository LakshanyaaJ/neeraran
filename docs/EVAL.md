# NEERARAN (நீர்Aran) — Model Evaluation & Simulator Ground Truth Benchmark

This document details the quantitative evaluation framework scored by the jury for TCS Tech Day Challenge 12.

---

## 1. Ground Truth vs. Agent Prediction Paradigm

The physical simulator maintains an internal ground-truth state matrix:
- $\mathbf{Q}_{\text{true}}(t)$: Exact actual water flow injected or consumed at each block and pipe segment.
- $\mathbf{P}_{\text{true}}(t)$: Exact pipe pressure head at each sensor junction.
- $\mathbf{L}_{\text{true}}(t)$: Exact leak location, orifice size, and loss rate (litres/minute).
- $\mathbf{V}_{\text{vuln}}(t)$: True equity score and vulnerable zone reserve headroom.

The agents observe only sensor readouts corrupted by simulated Gaussian measurement noise:
$$\tilde{y}(t) = y_{\text{true}}(t) + \epsilon, \quad \epsilon \sim \mathcal{N}(0, \sigma^2)$$

---

## 2. Quantitative Scoring Metrics

### Metric 1: Leak Detection Precision & Recall
$$\text{Precision} = \frac{\text{True Positives}}{\text{True Positives} + \text{False Positives}}$$
$$\text{Recall} = \frac{\text{True Positives}}{\text{True Positives} + \text{False Negatives}}$$
*Target*: Precision $\ge 0.90$, Recall $\ge 0.85$.

### Metric 2: Mean Absolute Percentage Error (MAPE) on Demand Forecast
$$\text{MAPE} = \frac{100\%}{N} \sum_{i=1}^N \left| \frac{D_{\text{true}, i} - \hat{D}_{\text{agent}, i}}{D_{\text{true}, i}} \right|$$
*Target*: Diurnal 24-hour demand forecast $\text{MAPE} \le 7.5\%$.

### Metric 3: Water Conservation Index (Total kL Saved)
$$\Delta W_{\text{saved}} = \int_{t_{\text{detected}}}^{t_{\text{isolated}}} \left( L_{\text{leak rate}}(t) - L_{\text{post-intervention}}(t) \right) dt + W_{\text{STP recycled}}$$
*Target*: Over 45 kL saved daily via automated isolation and recycled STP reuse.

### Metric 4: Vulnerable Zone Equity Violations
Count of incidents where supply to hostels, daycare, or health clinic fell below emergency threshold:
$$\text{Violations} = \sum_{t} \mathbb{I}(\text{Supply}_{\text{vulnerable}}(t) < \text{Threshold}_{\text{min}})$$
*Target*: Strict **0 violations** enforced by the guardrail engine.

### Metric 5: Plan Verification Fidelity
$$\text{Fidelity} = \frac{\text{Propositions Accepted with Valid } EVID}{\text{Total Propositions Generated}}$$
*Target*: $100\%$; all hallucinated or unsubstantiated claims are rejected by the Verifier Agent.

