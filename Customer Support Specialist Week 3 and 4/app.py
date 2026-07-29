"""Stage 4 — Jordan's Ticket Triage Assistant (Streamlit UI).

The payoff of the whole pipeline: instead of opening an unsorted queue and
running an AI assistant ticket-by-ticket, Jordan opens an already-sorted list.
This app reads the batch job's ``classified_tickets.json`` and renders:

  * a queue view sorted by priority + urgency score, with Zendesk-ish accents
    and a (simulated) SLA countdown;
  * a detail view that leads with the customer's own words, then the
    plain-language rationale and suggested queue;
  * a confirm / adjust control — the agent always has final say — that logs
    every override to ``results/override_log.csv`` for the manual spot-check.

Run:  ``streamlit run app.py``
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import json
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent
# Prefer the full generated batch; fall back to the committed demo sample.
DATA_CANDIDATES = [
    REPO_ROOT / "data" / "processed" / "classified_tickets.json",
    REPO_ROOT / "data" / "processed" / "classified_tickets.sample.json",
]
OVERRIDE_LOG = REPO_ROOT / "results" / "override_log.csv"

# Product priority scale → (emoji, accent colour, SLA target in hours).
#
# Accent colours are the severity ramp from the portfolio's DESIGN.md. They
# replace the original Material palette, whose amber (#fbc02d) sat at roughly
# 1.6:1 against the white surface — legible as a dot, unreadable as text.
# Every colour below clears WCAG AA (4.5:1) on both #FFFFFF and #FAFAFA.
CATEGORY_STYLE: Dict[str, Dict[str, object]] = {
    "Critical": {"emoji": "🔴", "color": "#C1300B", "sla_hours": 1},
    "High": {"emoji": "🟠", "color": "#A45709", "sla_hours": 4},
    "Medium": {"emoji": "🟡", "color": "#846800", "sla_hours": 24},
    "Low": {"emoji": "🟢", "color": "#3F6B4A", "sla_hours": 72},
}
CATEGORY_ORDER = ["Critical", "High", "Medium", "Low"]
QUEUE_OPTIONS = [
    "Technical Support", "IT Support", "Product Support", "Customer Service",
    "Billing and Payments", "Service Outages and Maintenance",
    "Returns and Exchanges", "Sales and Pre-Sales", "Human Resources", "General Inquiry",
]


# --- Presentation -------------------------------------------------------------

# Streamlit's defaults are tuned for dashboards, not for reading. Triage is a
# reading task: the agent's job is to absorb a customer's message and make a
# call. So the type scale is raised, the measure is capped, and the panels
# animate in on selection so a rerun reads as "new ticket loaded" rather than
# as a flicker. Motion is disabled under prefers-reduced-motion.
APP_CSS = """
<style>
  :root {
    --tri-ink: #1A1A1E;
    --tri-body: #3F3F46;
    --tri-muted: #63636E;
    --tri-rule: #E4E4E9;
    --tri-surface: #FFFFFF;
    --tri-accent: #4F46E5;
  }

  /* ---- Type scale: the headline fix. Streamlit ships ~14px in dense
     widgets; triage copy needs to be readable at a glance. ---- */
  html, body, .stApp, [data-testid="stAppViewContainer"] {
    font-size: 17px;
  }
  .stMarkdown p, .stMarkdown li {
    font-size: 1rem;
    line-height: 1.68;
    color: var(--tri-body);
  }
  h1, h2, h3, h4 { color: var(--tri-ink); letter-spacing: -0.015em; }
  [data-testid="stHeading"] h1 { font-size: 2.1rem; }
  [data-testid="stHeading"] h2 { font-size: 1.45rem; }
  [data-testid="stHeading"] h3 { font-size: 1.2rem; }

  /* Queue table: bigger rows, readable cells, no cramped 12px text. */
  [data-testid="stDataFrame"] { font-size: 0.95rem; }
  [data-testid="stDataFrame"] [role="gridcell"] { padding-top: 6px; padding-bottom: 6px; }

  /* KPI row */
  [data-testid="stMetricValue"] { font-size: 1.9rem; font-weight: 650; }
  [data-testid="stMetricLabel"] { font-size: 0.9rem; }

  /* ---- Motion: panels arrive, they don't blink into place ---- */
  @keyframes triageRise {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: none; }
  }
  .tri-animate { animation: triageRise 260ms cubic-bezier(0.22, 1, 0.36, 1) both; }
  .tri-delay-1 { animation-delay: 45ms; }
  .tri-delay-2 { animation-delay: 90ms; }

  /* ---- Ticket header ---- */
  .tri-head {
    border-left: 5px solid var(--cat-color, var(--tri-accent));
    padding: 0.55rem 0 0.55rem 0.95rem;
    margin-bottom: 1.1rem;
  }
  .tri-head-top {
    font-size: 1.22rem; font-weight: 650; color: var(--tri-ink);
    line-height: 1.3; margin-bottom: 0.2rem;
  }
  .tri-head-sub { font-size: 1rem; color: var(--tri-muted); line-height: 1.5; }

  /* ---- Conversation panel: the customer's own words, always visible ---- */
  .tri-convo {
    border: 1px solid var(--tri-rule);
    border-radius: 10px;
    background: var(--tri-surface);
    overflow: hidden;
    margin-bottom: 1.1rem;
  }
  .tri-convo-bar {
    display: flex; align-items: baseline; justify-content: space-between;
    gap: 12px; padding: 0.6rem 1rem;
    background: #F6F6F9; border-bottom: 1px solid var(--tri-rule);
  }
  .tri-convo-who {
    font-size: 0.78rem; font-weight: 650; letter-spacing: 0.07em;
    text-transform: uppercase; color: var(--tri-muted);
  }
  .tri-convo-id {
    font-size: 0.78rem; color: var(--tri-muted);
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
  }
  .tri-convo-subject {
    padding: 0.9rem 1rem 0.2rem;
    font-size: 1.06rem; font-weight: 620; color: var(--tri-ink); line-height: 1.4;
  }
  .tri-convo-body {
    padding: 0.5rem 1rem 1rem;
    font-size: 1rem; line-height: 1.72; color: var(--tri-body);
    max-width: 68ch; white-space: pre-wrap; word-break: break-word;
  }
  .tri-convo-empty { color: var(--tri-muted); font-style: italic; }
  .tri-tags { padding: 0 1rem 0.95rem; display: flex; flex-wrap: wrap; gap: 6px; }
  .tri-tag {
    font-size: 0.76rem; color: var(--tri-muted);
    border: 1px solid var(--tri-rule); border-radius: 4px; padding: 2px 8px;
  }

  /* ---- Fact rows (replaces st.metric in the detail pane, which would
     otherwise be summed by the queue-size regression test) ---- */
  .tri-facts { border-top: 1px solid var(--tri-rule); margin-bottom: 1rem; }
  .tri-fact {
    display: flex; align-items: baseline; gap: 14px;
    padding: 0.6rem 0.15rem; border-bottom: 1px solid var(--tri-rule);
  }
  .tri-fact-key {
    flex: 0 0 9.5rem; font-size: 0.78rem; font-weight: 600;
    letter-spacing: 0.07em; text-transform: uppercase; color: var(--tri-muted);
  }
  .tri-fact-val { font-size: 1rem; color: var(--tri-ink); }
  .tri-fact-val .tri-sig {
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
    font-size: 0.88rem; color: var(--tri-body);
  }

  .tri-empty {
    border: 1px dashed var(--tri-rule); border-radius: 10px;
    padding: 2.2rem 1.5rem; text-align: center; color: var(--tri-muted);
    font-size: 1rem; line-height: 1.6;
  }
  .tri-empty-hint { display: inline-block; margin-top: 0.35rem; font-size: 0.92rem; opacity: 0.85; }

  /* Buttons and inputs: bigger tap targets, smooth state changes. */
  .stButton button {
    font-size: 0.98rem; font-weight: 600; padding: 0.5rem 1rem;
    border-radius: 8px; transition: transform 140ms ease, box-shadow 140ms ease,
      background-color 140ms ease, border-color 140ms ease;
  }
  .stButton button:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(26, 26, 30, 0.10);
  }
  .stButton button:active:not(:disabled) { transform: translateY(0); }

  section[data-testid="stSidebar"] { font-size: 0.98rem; }

  @media (prefers-reduced-motion: reduce) {
    .tri-animate { animation: none !important; }
    .stButton button { transition: none !important; }
    .stButton button:hover:not(:disabled) { transform: none !important; }
  }
</style>
"""


def inject_css() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


# --- Data loading ------------------------------------------------------------

@st.cache_data
def load_tickets() -> List[Dict]:
    for path in DATA_CANDIDATES:
        if path.exists():
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
    return []


def simulated_age_hours(ticket_id: str) -> float:
    """Deterministic pseudo-age so the SLA demo is stable across reruns.

    The dataset carries no timestamps, so intake time is simulated from a hash of
    the ticket id — clearly a demo aid, not real data.
    """
    digest = int(hashlib.sha256(ticket_id.encode()).hexdigest(), 16)
    return (digest % (48 * 60)) / 60.0  # 0–48 hours, in fractional hours


def sla_state(category: str, age_hours: float) -> str:
    target = CATEGORY_STYLE[category]["sla_hours"]
    remaining = target - age_hours
    if remaining <= 0:
        return "⚠️ breached"
    if remaining <= target * 0.25:
        return f"⏳ {remaining:.1f}h left"
    return f"{remaining:.1f}h left"


# --- Override logging ---------------------------------------------------------

def log_override(ticket_id: str, ai_category: str, agent_category: str, action: str) -> None:
    """Append a confirm/adjust decision to results/override_log.csv."""
    OVERRIDE_LOG.parent.mkdir(parents=True, exist_ok=True)
    is_new = not OVERRIDE_LOG.exists()
    with open(OVERRIDE_LOG, "a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        if is_new:
            writer.writerow(["timestamp", "ticket_id", "ai_category", "agent_category", "action"])
        writer.writerow([
            dt.datetime.now().isoformat(timespec="seconds"),
            ticket_id, ai_category, agent_category, action,
        ])


# --- Views -------------------------------------------------------------------

def render_queue(tickets: List[Dict]) -> Optional[int]:
    """Render the sorted queue table; return the selected row's positional index."""
    rows = []
    for t in tickets:
        cat = t["category"]
        age = simulated_age_hours(t["id"])
        # The safety-net flag rides along in the Priority cell rather than
        # claiming a column of its own. In a half-width pane every column costs
        # Subject width, and a truncated subject makes the queue unscannable —
        # which is the one job the queue has.
        shield = " 🛡️" if t.get("safety_net_triggered") else ""
        rows.append({
            "Priority": f"{CATEGORY_STYLE[cat]['emoji']} {cat}{shield}",
            "Score": t["score"],
            "Subject": t["subject"] or "(no subject)",
            "SLA": sla_state(cat, age),
        })
    df = pd.DataFrame(rows)

    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Priority": st.column_config.TextColumn(
                "Priority", width="small", help="🛡️ marks a Critical-class safety-net escalation"
            ),
            "Score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=100, format="%d", width="small"
            ),
            # "medium", not "large": a large Subject column is greedy enough to
            # push SLA out of the pane entirely. The countdown is the reason the
            # queue is scannable, so Subject yields the width instead.
            "Subject": st.column_config.TextColumn("Subject", width="medium"),
            "SLA": st.column_config.TextColumn("SLA", width="small"),
        },
        height=560,
    )
    selected = event.selection.rows
    return selected[0] if selected else None


def render_conversation(ticket: Dict) -> None:
    """The customer's own words — the thing you actually triage on.

    This used to live inside a collapsed ``st.expander("Ticket body")``, which
    meant the single most important piece of context on the screen took a click
    to reach. It now leads the detail pane.
    """
    subject = html.escape(ticket.get("subject") or "(no subject)")
    body = (ticket.get("body") or "").strip()
    body_html = (
        html.escape(body)
        if body
        else '<span class="tri-convo-empty">(no message body on this ticket)</span>'
    )
    tags = ticket.get("tags") or []
    tags_html = ""
    if tags:
        chips = "".join(f'<span class="tri-tag">{html.escape(str(tag))}</span>' for tag in tags)
        tags_html = f'<div class="tri-tags">{chips}</div>'

    st.markdown(
        f'<div class="tri-convo tri-animate tri-delay-1">'
        f'  <div class="tri-convo-bar">'
        f'    <span class="tri-convo-who">Customer wrote</span>'
        f'    <span class="tri-convo-id">{html.escape(str(ticket.get("id", "")))}</span>'
        f'  </div>'
        f'  <div class="tri-convo-subject">{subject}</div>'
        f'  <div class="tri-convo-body">{body_html}</div>'
        f'  {tags_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_detail(ticket: Dict) -> None:
    cat = ticket["category"]
    style = CATEGORY_STYLE[cat]

    st.markdown(
        f'<div class="tri-head tri-animate" style="--cat-color:{style["color"]}">'
        f'  <div class="tri-head-top">{style["emoji"]} {html.escape(cat)}'
        f'    &nbsp;·&nbsp; score {int(ticket["score"])}/100</div>'
        f'  <div class="tri-head-sub">{html.escape(ticket.get("subject") or "(no subject)")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if ticket.get("safety_net_triggered"):
        st.warning("🛡️ Critical-class safety net escalated this ticket to at least High.")

    # Lead with what the customer said, then explain the score.
    render_conversation(ticket)

    st.markdown("**Why this priority**")
    for bullet in ticket.get("rationale", []) or ["(run the Claude layer for a rationale)"]:
        st.markdown(f"- {bullet}")

    signals = ticket.get("matched_signals") or []
    signals_html = (
        f'<span class="tri-sig">{html.escape(", ".join(str(s) for s in signals))}</span>'
        if signals
        else '<span class="tri-sig">none</span>'
    )
    # Deliberately NOT st.metric: the queue-size regression test in
    # tests/test_app_smoke.py sums every metric that isn't "Tickets in queue",
    # so any metric rendered here would corrupt that assertion.
    st.markdown(
        f'<div class="tri-facts tri-animate tri-delay-2">'
        f'  <div class="tri-fact"><span class="tri-fact-key">Suggested queue</span>'
        f'    <span class="tri-fact-val">{html.escape(ticket.get("suggested_queue") or "—")}</span></div>'
        f'  <div class="tri-fact"><span class="tri-fact-key">Signals ({len(signals)})</span>'
        f'    <span class="tri-fact-val">{signals_html}</span></div>'
        f'  <div class="tri-fact"><span class="tri-fact-key">Dataset label</span>'
        f'    <span class="tri-fact-val">priority {html.escape(str(ticket.get("true_priority", "—")))}'
        f'      &nbsp;·&nbsp; queue {html.escape(str(ticket.get("true_queue", "—")))}</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    render_confirm_adjust(ticket)


def render_confirm_adjust(ticket: Dict) -> None:
    """The 'agent has final say' control — accept or override the category."""
    st.markdown("**Agent decision** — the system recommends; you decide.")
    cat = ticket["category"]
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("✅ Confirm", use_container_width=True, key=f"confirm_{ticket['id']}"):
            log_override(ticket["id"], cat, cat, "confirm")
            st.session_state["last_action"] = {
                "ticket": ticket["id"],
                "msg": f"Confirmed {ticket['id']} as {cat}.",
            }
    with col2:
        new_cat = st.selectbox(
            "Override category", CATEGORY_ORDER,
            index=CATEGORY_ORDER.index(cat), key=f"ovr_{ticket['id']}",
        )
        if st.button("✏️ Save override", use_container_width=True,
                     disabled=(new_cat == cat), key=f"save_{ticket['id']}"):
            log_override(ticket["id"], cat, new_cat, "override")
            st.session_state["last_action"] = {
                "ticket": ticket["id"],
                "msg": f"Overrode {ticket['id']}: {cat} → {new_cat}.",
            }

    # The confirmation is scoped to the ticket it belongs to. Keying this on a
    # bare string meant the banner followed the agent to the NEXT ticket: after
    # confirming T00005, opening T00051 still showed "Confirmed T00005", which
    # reads as "you already handled this one" on a ticket nobody has touched.
    last = st.session_state.get("last_action")
    if isinstance(last, dict) and last.get("ticket") == ticket["id"]:
        st.success(last["msg"])


@st.fragment
def render_workspace(filtered: List[Dict]) -> None:
    """Queue + detail, isolated in a fragment.

    Selecting a row used to rerun the whole script: sidebar, filters, KPI row and
    all. Scoping both panes into one fragment means a click reruns only this
    block, which is what makes selection feel immediate instead of janky.
    """
    left, right = st.columns([1.25, 1], gap="large")
    with left:
        st.subheader("Queue")
        if not filtered:
            # An empty DataFrame still renders a 560px grid skeleton with no
            # columns and a tiny grey "empty" label, which reads as a broken
            # table rather than "your filters matched nothing".
            st.markdown(
                '<div class="tri-empty">No tickets match these filters.<br>'
                '<span class="tri-empty-hint">Clear the search box, or re-add a'
                ' priority in the sidebar.</span></div>',
                unsafe_allow_html=True,
            )
            selected_idx = None
        else:
            selected_idx = render_queue(filtered)
    with right:
        st.subheader("Ticket detail")
        if selected_idx is not None and selected_idx < len(filtered):
            render_detail(filtered[selected_idx])
        else:
            st.markdown(
                '<div class="tri-empty">Select a ticket in the queue to read the'
                ' customer\'s message, see why it scored the way it did, and act on it.</div>',
                unsafe_allow_html=True,
            )


# --- App ---------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Jordan's Ticket Triage", page_icon="🎫", layout="wide")
    inject_css()
    st.title("🎫 Jordan's Ticket Triage Assistant")
    st.caption("A pre-sorted support queue: priority, urgency score, and a plain-language why.")

    tickets = load_tickets()
    if not tickets:
        st.error(
            "No classified tickets found. Run `python -m src.batch_classify` "
            "(after `python src/data_prep.py`) to generate them."
        )
        return

    with st.sidebar:
        st.header("Filters")
        chosen = st.multiselect("Priority", CATEGORY_ORDER, default=CATEGORY_ORDER)
        query = st.text_input("Search subject/body")
        only_net = st.checkbox("Only safety-net escalations")

    filtered = [
        t for t in tickets
        if t["category"] in chosen
        and (not only_net or t.get("safety_net_triggered"))
        and (not query or query.lower() in (t["subject"] + " " + t["body"]).lower())
    ]

    with st.sidebar:
        st.markdown("---")
        # Reflect the *filtered* queue size, not the full dataset — otherwise the
        # metric reads 800 while the queue shows a handful (found by /qa).
        st.metric("Tickets in queue", len(filtered))

    counts = {c: sum(1 for t in filtered if t["category"] == c) for c in CATEGORY_ORDER}
    cols = st.columns(4)
    for col, c in zip(cols, CATEGORY_ORDER):
        col.metric(f"{CATEGORY_STYLE[c]['emoji']} {c}", counts[c])

    render_workspace(filtered)


if __name__ == "__main__":
    main()
