"""Stage 4 — Jordan's Ticket Triage Assistant (Streamlit UI).

The payoff of the whole pipeline: instead of opening an unsorted queue and
running an AI assistant ticket-by-ticket, Jordan opens an already-sorted list.
This app reads the batch job's ``classified_tickets.json`` and renders:

  * a paginated queue view sorted by priority + urgency score, card-based with
    a real click-to-select state and a (simulated) SLA countdown;
  * a detail view with the plain-language rationale and suggested queue;
  * a confirm / adjust control — the agent always has final say — that logs
    every override to ``results/override_log.csv`` for the manual spot-check.

Visual identity, spacing, and CSS-scoping decisions here follow the locked
Design Tokens in the design doc (see office-hours + plan-design-review +
plan-eng-review artifacts under ~/.gstack/projects/).

Run:  ``streamlit run app.py``
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent
# Prefer the full generated batch; fall back to the committed demo sample.
DATA_CANDIDATES = [
    REPO_ROOT / "data" / "processed" / "classified_tickets.json",
    REPO_ROOT / "data" / "processed" / "classified_tickets.sample.json",
]
OVERRIDE_LOG = REPO_ROOT / "results" / "override_log.csv"

# --- Design Tokens (locked) ---------------------------------------------------
# Colors, type scale, spacing, and radii below match the design doc's "Design
# Tokens" section. .streamlit/config.toml carries base=light + the primary
# accent/background/text colors; anything config.toml can't express (scoped
# selectors, the Inter font import, the responsive media query) is injected
# once via inject_css(), never per-row.
BG = "#FAFAFA"
SURFACE = "#FFFFFF"
BORDER = "#E5E5E7"
TEXT = "#1A1A1E"
TEXT_MUTED = "#4B5563"
ACCENT = "#4F46E5"
ACCENT_TINT = "#EEF2FF"

# Product priority scale → badge colors (WCAG AA-checked pairs), SLA target.
CATEGORY_STYLE: Dict[str, Dict[str, object]] = {
    "Critical": {"badge_bg": "#FEE2E2", "badge_text": "#991B1B", "sla_hours": 1},
    "High": {"badge_bg": "#FFEDD5", "badge_text": "#9A3412", "sla_hours": 4},
    "Medium": {"badge_bg": "#FEF9C3", "badge_text": "#854D0E", "sla_hours": 24},
    "Low": {"badge_bg": "#DCFCE7", "badge_text": "#166534", "sla_hours": 72},
}
CATEGORY_ORDER = ["Critical", "High", "Medium", "Low"]
QUEUE_OPTIONS = [
    "Technical Support", "IT Support", "Product Support", "Customer Service",
    "Billing and Payments", "Service Outages and Maintenance",
    "Returns and Exchanges", "Sales and Pre-Sales", "Human Resources", "General Inquiry",
]

PAGE_SIZE = 50  # queue pagination — see design doc "Pagination" (critical fix)


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
        return "⚠ breached"
    if remaining <= target * 0.25:
        return f"⏳ {remaining:.1f}h left"
    return f"{remaining:.1f}h left"


# --- Override logging ---------------------------------------------------------

def log_override(ticket_id: str, ai_category: str, agent_category: str, action: str) -> bool:
    """Append a confirm/adjust decision to results/override_log.csv.

    Returns True on success. On failure (e.g. a read-only results/ directory),
    shows a user-visible error instead of letting the exception crash the rerun.
    """
    try:
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
        return True
    except OSError:
        st.error("Couldn't save your decision — try again.")
        return False


# --- Styling -------------------------------------------------------------------

def inject_css() -> None:
    """Inject all CSS this app needs, once, regardless of ticket count.

    Selector scoping (eng review): ticket_queue and detail_actions are two
    separately-keyed containers so the ghost-button rule for queue rows never
    bleeds into the detail panel's Confirm/Save-override buttons, and vice
    versa — no carve-outs from "no default Streamlit chrome showing through."
    """
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] {{
            font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }}
        /* Slim header per the wireframe — st.title() is kept (not swapped for
           st.markdown) so AppTest's at.title collection still finds it. */
        [data-testid="stAppViewContainer"] h1 {{
            font-size: 22px !important;
            margin-bottom: 0 !important;
        }}
        .badge-chip {{
            display: inline-block;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 13px;
            font-weight: 600;
            white-space: nowrap;
        }}
        .empty-state {{
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 24px;
            text-align: center;
            color: {TEXT_MUTED};
            font-size: 16px;
        }}
        /* Queue rows: ghost-skinned buttons as the click target. Scoped to
           .st-key-ticket_queue only — does not touch detail_actions. */
        .st-key-ticket_queue div[data-testid="stButton"] button {{
            border: none;
            background: transparent;
            text-align: left;
            width: 100%;
            padding: 8px 4px;
            font-size: 16px;
            color: {TEXT};
        }}
        .st-key-ticket_queue div[data-testid="stButton"] button:hover {{
            color: {ACCENT};
        }}
        .st-key-ticket_queue div[data-testid="stButton"] button:focus-visible {{
            outline: 2px solid {ACCENT};
            outline-offset: 2px;
        }}
        /* Detail panel action buttons: their own scope, own styling — not a
           default-styling carve-out (eng review contradiction fix). */
        .st-key-detail_actions div[data-testid="stButton"] button {{
            border-radius: 6px;
            border: 1px solid {BORDER};
        }}
        .st-key-detail_actions div[data-testid="stButton"] button:focus-visible {{
            outline: 2px solid {ACCENT};
            outline-offset: 2px;
        }}
        /* Responsive: below ~900px, stack the queue/detail split vertically
           instead of side-by-side (design doc "Responsive & Accessibility"). */
        @media (max-width: 900px) {{
            .st-key-queue_detail_split div[data-testid="stHorizontalBlock"] {{
                flex-direction: column;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _selected_row_css(position: Optional[int]) -> None:
    """Give the selected row's own bordered container an accent outline.

    Scoped by within-page position (not ticket id) so it stays CSS-safe
    regardless of what characters appear in real ticket ids.
    """
    if position is None:
        return
    st.markdown(
        f"<style>.st-key-row_container_{position} "
        f"{{ border-color: {ACCENT} !important; background: {ACCENT_TINT} !important; }}</style>",
        unsafe_allow_html=True,
    )


# --- Views -------------------------------------------------------------------

def render_queue(tickets: List[Dict], confirmed_ids: Set[str]) -> Optional[str]:
    """Render the paginated, card-based queue. Returns the selected ticket id."""
    if not tickets:
        st.markdown(
            "<div class='empty-state'>No tickets match your filters.</div>",
            unsafe_allow_html=True,
        )
        if st.button("Clear filters"):
            st.session_state["_reset_filters"] = True
            st.rerun()
        return st.session_state.get("selected_ticket_id")

    total = len(tickets)
    page_count = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(st.session_state.get("queue_page", 0), page_count - 1)
    st.session_state["queue_page"] = page
    start = page * PAGE_SIZE
    page_tickets = tickets[start:start + PAGE_SIZE]

    selected_id = st.session_state.get("selected_ticket_id")
    selected_position = next(
        (i for i, t in enumerate(page_tickets) if t["id"] == selected_id), None
    )
    _selected_row_css(selected_position)

    with st.container(key="ticket_queue"):
        for i, t in enumerate(page_tickets):
            cat = t["category"]
            style = CATEGORY_STYLE[cat]
            age = simulated_age_hours(t["id"])
            with st.container(key=f"row_container_{i}", border=True):
                col_badge, col_row = st.columns([1, 5])
                with col_badge:
                    badge_html = (
                        f"<span class='badge-chip' style='background:{style['badge_bg']};"
                        f"color:{style['badge_text']}'>{cat.upper()}</span>"
                    )
                    if t.get("safety_net_triggered"):
                        badge_html += (
                            " <span title='Safety-net escalated to at least High' "
                            "aria-label='Safety-net escalated to at least High'>🛡️</span>"
                        )
                    st.markdown(badge_html, unsafe_allow_html=True)
                with col_row:
                    label = (
                        f"{t['subject'] or '(no subject)'}  ·  "
                        f"{t.get('suggested_queue') or '—'}  ·  {sla_state(cat, age)}"
                    )
                    if t["id"] in confirmed_ids:
                        label = f"✓ {label}"
                    if st.button(label, key=f"row_{t['id']}", use_container_width=True):
                        st.session_state["selected_ticket_id"] = t["id"]

    nav_prev, nav_info, nav_next = st.columns([1, 2, 1])
    with nav_prev:
        if st.button("← Previous", disabled=(page == 0), key="queue_prev"):
            st.session_state["queue_page"] = page - 1
            st.rerun()
    with nav_info:
        st.caption(f"Page {page + 1} of {page_count} ({total} tickets)")
    with nav_next:
        if st.button("Next →", disabled=(page >= page_count - 1), key="queue_next"):
            st.session_state["queue_page"] = page + 1
            st.rerun()

    return st.session_state.get("selected_ticket_id")


def render_detail(ticket: Dict) -> None:
    cat = ticket["category"]
    style = CATEGORY_STYLE[cat]
    st.markdown(
        f"<div style='border-left:4px solid {style['badge_text']};padding:0.4rem 0.9rem;'>"
        f"<span class='badge-chip' style='background:{style['badge_bg']};"
        f"color:{style['badge_text']}'>{cat.upper()}</span>"
        f"<span style='margin-left:8px;font-size:16px'>score {ticket['score']}/100</span>"
        f"<div style='color:{TEXT_MUTED};font-size:16px;margin-top:4px'>"
        f"{ticket['subject'] or '(no subject)'}</div></div>",
        unsafe_allow_html=True,
    )

    if ticket.get("safety_net_triggered"):
        st.warning("🛡️ Critical-class safety net escalated this ticket to at least High.")

    st.markdown("**Why this priority**")
    for bullet in ticket.get("rationale", []) or ["(run the Claude layer for a rationale)"]:
        st.markdown(f"- {bullet}")

    col1, col2 = st.columns(2)
    col1.metric("Suggested queue", ticket.get("suggested_queue") or "—")
    signals = ticket.get("matched_signals") or []
    col2.metric("Signals matched", len(signals))
    if signals:
        col2.caption(", ".join(signals))

    with st.expander("Ticket body"):
        st.write(ticket.get("body") or "(empty)")

    with st.expander("Ground-truth labels (from dataset, for reference)"):
        st.write(f"Priority label: **{ticket.get('true_priority', '—')}**")
        st.write(f"Queue label: **{ticket.get('true_queue', '—')}**")

    render_confirm_adjust(ticket)


def render_confirm_adjust(ticket: Dict) -> None:
    """The 'agent has final say' control — accept or override the category."""
    st.markdown("---")
    st.markdown("**Agent decision** — the system recommends; you decide.")
    cat = ticket["category"]
    with st.container(key="detail_actions"):
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("✅ Confirm", use_container_width=True):
                if log_override(ticket["id"], cat, cat, "confirm"):
                    st.session_state["confirmed_ids"].add(ticket["id"])
                    st.toast(f"Confirmed {ticket['id']} as {cat}.", icon="✅")
                    st.rerun()
        with col2:
            new_cat = st.selectbox(
                "Override category", CATEGORY_ORDER,
                index=CATEGORY_ORDER.index(cat), key=f"ovr_{ticket['id']}",
            )
            if st.button("✏️ Save override", use_container_width=True, disabled=(new_cat == cat)):
                if log_override(ticket["id"], cat, new_cat, "override"):
                    st.session_state["confirmed_ids"].add(ticket["id"])
                    st.toast(f"Overrode {ticket['id']}: {cat} → {new_cat}.", icon="✏️")
                    st.rerun()


# --- App ---------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="Jordan's Ticket Triage", page_icon="🎫", layout="wide")
    inject_css()

    tickets = load_tickets()
    if not tickets:
        st.error(
            "No classified tickets found. Run `python -m src.batch_classify` "
            "(after `python src/data_prep.py`) to generate them."
        )
        return

    st.session_state.setdefault("confirmed_ids", set())
    st.session_state.setdefault("queue_page", 0)
    st.session_state.setdefault("selected_ticket_id", None)

    # Deferred filter reset (eng review pattern): a widget's session_state key
    # can't be reassigned after that widget has already been instantiated this
    # run, so "Clear filters" (inside render_queue, called later) sets a flag
    # and reruns; we consume the flag here, before the sidebar widgets exist.
    if st.session_state.pop("_reset_filters", False):
        st.session_state["filter_priority"] = CATEGORY_ORDER
        st.session_state["filter_query"] = ""
        st.session_state["filter_only_net"] = False

    with st.sidebar:
        st.header("Filters")
        chosen = st.multiselect(
            "Priority", CATEGORY_ORDER, default=CATEGORY_ORDER, key="filter_priority"
        )
        query = st.text_input("Search subject/body", key="filter_query")
        only_net = st.checkbox("Only safety-net escalations", key="filter_only_net")
        st.markdown("---")
        st.metric("Tickets in queue", len(tickets))

    filtered = [
        t for t in tickets
        if t["category"] in chosen
        and (not only_net or t.get("safety_net_triggered"))
        and (not query or query.lower() in (t["subject"] + " " + t["body"]).lower())
    ]

    # Reset to page 1 whenever the filtered result set changes shape, so a
    # stale queue_page from a larger previous result set can't point past the
    # end of a newly-narrowed one.
    filter_signature = (tuple(sorted(chosen)), query, only_net)
    if st.session_state.get("_last_filter_signature") != filter_signature:
        st.session_state["queue_page"] = 0
        st.session_state["_last_filter_signature"] = filter_signature

    counts = {c: sum(1 for t in filtered if t["category"] == c) for c in CATEGORY_ORDER}
    header_cols = st.columns([3, 1, 1, 1, 1])
    with header_cols[0]:
        st.title("🎫 Jordan's Ticket Triage")
        st.caption("A pre-sorted support queue: priority, urgency score, and a plain-language why.")
    for col, c in zip(header_cols[1:], CATEGORY_ORDER):
        style = CATEGORY_STYLE[c]
        col.markdown(
            f"<div style='border:1px solid {BORDER};border-radius:8px;padding:6px 10px;"
            f"text-align:center;background:{SURFACE}'>"
            f"<div style='font-size:13px;color:{TEXT_MUTED}'>{c}</div>"
            f"<div style='font-size:16px;font-weight:600;color:{TEXT}'>{counts[c]}</div></div>",
            unsafe_allow_html=True,
        )

    with st.container(key="queue_detail_split"):
        left, right = st.columns([3, 2])
        with left:
            st.subheader("Queue")
            selected_id = render_queue(filtered, st.session_state["confirmed_ids"])
        with right:
            st.subheader("Ticket detail")
            selected_ticket = next((t for t in filtered if t["id"] == selected_id), None)
            if selected_ticket is not None:
                render_detail(selected_ticket)
            else:
                st.info("Select a ticket in the queue to see its rationale and act on it.")


if __name__ == "__main__":
    main()
