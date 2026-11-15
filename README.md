# FreightFlow: AI Inbox & Shipping Document Automation

An AI automation system for a freight forwarder's daily email and paperwork workload. Built as an assignment for the **AI Intern** role at **Prologis Freight India Pvt Ltd**.

## The problem

A forwarding desk gets a steady stream of emails: rate requests, "where is my shipment?", complaints, and attachments such as invoices, packing lists and bills of lading. Today each email is read, sorted and answered by hand. Each set of documents is also checked by eye.

That manual checking is where costly mistakes slip through. If the invoice says **2,450 kg** but the BL says **2,540 kg**, the container can be **held at customs**, demurrage starts, and the BL has to be amended for a fee.

## What FreightFlow does

```
Gmail ──► n8n ──► FreightFlow API (Python + Claude) ──► Google Sheets log
                        │                                   │
                        ├─ 1. Classify email + urgency       └─► Dashboard (impact)
                        ├─ 2. Extract fields from PDFs
                        ├─ 3. Cross-check documents (weight, HS, consignee…)
                        ├─ 4. Look up tracking status (TMS / CSV)
                        └─ 5. Draft reply ──► HUMAN REVIEW ──► send
                                               (nothing is sent automatically)
```

| Step | How |
|---|---|
| **Email triage** | Claude labels each email as quote request, shipment status, documentation, complaint, booking or other. It also sets urgency (high/medium/low), writes a one-line summary, and pulls out the reference, route, weight and containers. |
| **Document extraction** | PDF → text (pdfplumber) → Claude returns **typed JSON** using tool-use with a JSON Schema: shipper, consignee, ports, HS codes, packages, gross weight, value, Incoterms. |
| **Cross-checks** | Compares documents from the same shipment and flags mismatched weight (with a 0.5% tolerance), packages, parties or ports, and missing HS codes. |
| **Shipment history** | Links emails about the same shipment (by booking ref, BL or AWB no.). If an earlier email's documents had a mismatch, a later "why is my container held?" email gets that context, so the reply names the likely cause. |
| **System connection** | Looks up the shipment in a tracking table so status replies use real data. `shipments.csv` stands in for the company TMS/API. |
| **Reply drafting** | Claude drafts a plain-text reply using only the facts it has (email, tracking, document issues, shipment history). It is told never to invent names, deadlines or reasons, or to promise refunds. Quotes get a `[RATE TO BE ADDED BY TEAM]` placeholder because prices are never invented. |
| **Human-in-the-loop** | Every draft waits in a review queue (`review.py` or the `/drafts` API). A person approves, edits or rejects it. Only approved drafts are sent. |
| **Logging & dashboard** | Everything goes into SQLite (and Google Sheets via n8n). The HTML dashboard shows volume, urgency, issues caught and estimated hours saved. |
| **Testing** | `evaluate.py` measures accuracy against hand-labelled ground truth. `tests/` holds unit tests. |

## Results on the sample data

Run in **mock mode** (a rule-based fallback, with no API key):

```
Email category accuracy: 10/10 = 100%
Urgency accuracy:        9/10  = 90%
Document field accuracy: 37/37 = 100%
Issues caught: BL weight 2540 kg vs invoice/PL 2450 kg; HS 6203.42.00 missing on BL
```

> Note: the mock rules were written against these samples, so these numbers are optimistic. Real emails and documents vary a lot. That is why the Claude mode exists: it handles any wording or layout. The honest test is to run `evaluate.py` on a new batch of real (anonymised) emails.

## Choosing the AI provider

Set `LLM_PROVIDER` in `.env`:

| Provider | Cost | Key from | Notes |
|---|---|---|---|
| `groq` | Free tier | console.groq.com | Open models (e.g. Llama), very fast, rate-limited |
| `gemini` | Free tier | aistudio.google.com | Gemini Flash models, rate-limited; free-tier data may be used by Google to improve products |

Groq and Gemini are called through their OpenAI-compatible endpoints using only the Python standard library. No extra packages are needed.

## Project Dashboard Preview

<img width="1899" height="915" alt="s_ai" src="https://github.com/user-attachments/assets/d927e83c-505f-4018-b411-0e6f01ba2d84" />



## Run it

```bash
pip install -r requirements.txt
cp .env.example .env            # choose LLM_PROVIDER and add its key (or leave empty for mock mode)

python run_demo.py              # processes sample inbox -> output/dashboard.html
python evaluate.py              # accuracy report
python review.py                # approve / edit / reject drafts
python tests/test_core.py       # unit tests

uvicorn api:app --reload        # API at http://localhost:8000/docs
```

### n8n

1. Start the API (`uvicorn api:app`) and n8n (`npx n8n` or n8n cloud).
2. In n8n, choose **Import from file** and pick `n8n/freightflow_workflow.json`.
3. Connect your Gmail and Google Sheets credentials. Set the Sheet ID and the ops alert email address.
4. The **main flow** is: Gmail trigger → prepare payload (PDFs as base64) → `/process-email` → log to Sheets → if the email is urgent or has a document issue, alert the ops team.
5. The **approval flow** is: the webhook `approve-draft` receives `{draft_id}`, marks the draft approved, and sends the reply to the customer.

## Design decisions

- **Human review before sending.** Replies to customers can carry commercial and legal weight, so the AI drafts and a person decides.
- **Structured outputs.** Claude's tool-use with a JSON Schema returns valid typed JSON, so no fragile text parsing is needed.
- **No invented facts.** Prompts tell Claude to use only the data provided. Missing values come back as `null`, and rates are placeholders.
- **Mock mode.** The whole pipeline runs and can be demoed with no API key, which also makes it cheap to test.
- **Python brain, no-code glue.** The logic lives in a tested Python service. n8n handles the connectors (Gmail, Sheets) and can be swapped for Make, Zapier or Power Automate.

