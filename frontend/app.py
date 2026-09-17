import os
import uuid
from collections import defaultdict

import requests
import streamlit as st



BACKEND_HOST = st.secrets["BACKEND_URL"].rstrip("/")
CHAT_URL = f"{BACKEND_HOST}/api/chat"
STATE_URL = f"{BACKEND_HOST}/api/state"
WEATHER_URL = f"{BACKEND_HOST}/api/weather"
CURRENCY_URL = f"{BACKEND_HOST}/api/currency"
EXPENSE_URL = f"{BACKEND_HOST}/api/state"
DEFAULT_BUDGET = 250_000.0

st.set_page_config(page_title="SafarAI Travel Agent", page_icon="✈️", layout="wide")


def initialize_session() -> None:
    defaults = {
        "thread_id": str(uuid.uuid4()),
        "show_welcome": True,
        "chat_history": [],
        "metrics": {"total_budget": DEFAULT_BUDGET, "spend": 0.0, "remaining": DEFAULT_BUDGET, "itinerary": []},
        "weather_result": None,
        "currency_result": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def request_json(method: str, url: str, **kwargs) -> dict:
    response = requests.request(method, url, timeout=60, **kwargs)
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("The backend returned an invalid response.") from exc
    if not response.ok:
        raise RuntimeError(payload.get("detail", "The backend could not complete that request."))
    return payload


def update_metrics(payload: dict) -> None:
    metrics = st.session_state.metrics
    metrics["total_budget"] = float(payload.get("total_budget_pkr", metrics["total_budget"]))
    metrics["spend"] = float(payload.get("current_spend", metrics["spend"]))
    metrics["remaining"] = float(payload.get("remaining_budget", metrics["remaining"]))
    metrics["itinerary"] = payload.get("itinerary", metrics["itinerary"])


def sync_thread_state() -> None:
    try:
        payload = request_json("GET", f"{STATE_URL}/{st.session_state.thread_id}")
        if payload.get("initialized"):
            update_metrics(payload)
    except (requests.RequestException, RuntimeError):
        pass


def reset_session() -> None:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.session_state.metrics = {"total_budget": DEFAULT_BUDGET, "spend": 0.0, "remaining": DEFAULT_BUDGET, "itinerary": []}
    st.session_state.weather_result = None
    st.session_state.currency_result = None


def format_error(error: Exception) -> str:
        return f"Backend error: {error}"


initialize_session()
sync_thread_state()

st.markdown(
    """
    <style>
    .block-container { max-width: 1180px; padding-top: 2.2rem; }
    :root { --olive: #65743a; --dark-olive: #3f4d22; --olive-pale: #f4f6ec; --line: #dfe5cf; --ink: #29311d; --muted: #6b7260; --white: #ffffff; }
    html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] { background: var(--white); color: var(--ink); }
    [data-testid="stHeader"] { background: var(--white); }
    [data-testid="stSidebar"] { background: var(--olive-pale); border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] * { color: var(--ink); }
    h1, h2, h3, h4, label, p { color: var(--ink); }
    [data-testid="stCaptionContainer"] p { color: var(--muted); }
    .app-kicker { color: var(--olive) !important; font-size: 0.78rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; text-align: center; }
    .app-title { color: var(--dark-olive) !important; font-size: 2.4rem; font-weight: 800; line-height: 1.05; margin: 0.2rem 0 0.35rem; text-align: center; }
    .app-subtitle { color: var(--muted) !important; font-size: 1rem; margin-bottom: 1.5rem; text-align: center; }
    .welcome-shell { max-width: 820px; margin: 8vh auto 0; padding: 3rem 2rem; text-align: center; background: var(--olive-pale); border: 1px solid var(--line); border-radius: 12px; }
    .welcome-mark { color: var(--olive); font-size: 2.2rem; margin-bottom: 0.75rem; }
    .welcome-title { color: var(--dark-olive); font-size: clamp(2rem, 5vw, 3.6rem); font-weight: 800; line-height: 1.05; margin-bottom: 0.75rem; }
    .welcome-copy { color: var(--muted); font-size: 1.05rem; line-height: 1.6; max-width: 620px; margin: 0 auto 1.8rem; }
    .feature-list { color: var(--ink); display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.75rem; text-align: left; max-width: 620px; margin: 0 auto 2rem; }
    .feature-item { background: var(--white); border: 1px solid var(--line); border-radius: 8px; padding: 0.85rem 1rem; }
    [data-testid="stMetric"] { background: var(--olive-pale); border: 1px solid var(--line); padding: 1rem; border-radius: 8px; }
    [data-testid="stMetricValue"] { color: var(--dark-olive); }
    button[kind="primary"] { background: var(--olive); border-color: var(--olive); }
    button[kind="primary"]:hover { background: var(--dark-olive); border-color: var(--dark-olive); }
    div[data-baseweb="tab-list"] { gap: 0.5rem; }
    button[data-baseweb="tab"] { color: var(--muted); font-weight: 650; }
    button[data-baseweb="tab"][aria-selected="true"] { color: var(--dark-olive); border-bottom-color: var(--olive); }
    [data-testid="stChatMessage"] { background: var(--olive-pale); border: 1px solid var(--line); border-radius: 8px; margin-bottom: 0.7rem; }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] em,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] blockquote,
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] a { color: var(--ink) !important; }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] code { color: var(--dark-olive) !important; background: var(--white); }
    [data-testid="stChatInput"] { border-color: var(--dark-olive); background: var(--dark-olive); }
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] input { color: var(--white) !important; background: var(--dark-olive) !important; -webkit-text-fill-color: var(--white) !important; }
    input, textarea,
    [data-baseweb="select"] input,
    [data-baseweb="select"] > div { color: var(--ink) !important; background: var(--white) !important; border-color: var(--line) !important; -webkit-text-fill-color: var(--ink) !important; }
    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] input { color: var(--white) !important; background: var(--dark-olive) !important; -webkit-text-fill-color: var(--white) !important; }
    input::placeholder, textarea::placeholder,
    [data-baseweb="select"] input::placeholder { color: #65705b !important; opacity: 1 !important; -webkit-text-fill-color: #65705b !important; }
    [data-testid="stChatInput"] textarea::placeholder,
    [data-testid="stChatInput"] input::placeholder { color: #dfe5cf !important; -webkit-text-fill-color: #dfe5cf !important; }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] { color: var(--ink) !important; }
    [data-testid="stProgressBar"] > div > div { background: var(--olive); }
    .empty-state { background: var(--olive-pale); border: 1px dashed #c5cfaa; border-radius: 8px; padding: 1.25rem; color: var(--muted); }
    @media (max-width: 720px) {
        .block-container { padding: 1.25rem 1rem 2rem; }
        .app-title { font-size: 1.85rem; }
        .app-subtitle { font-size: 0.92rem; }
        div[data-baseweb="tab-list"] { overflow-x: auto; flex-wrap: nowrap; }
        button[data-baseweb="tab"] { min-width: max-content; padding-left: 0.65rem; padding-right: 0.65rem; }
        .welcome-shell { margin-top: 3vh; padding: 2rem 1rem; }
        .feature-list { grid-template-columns: 1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.session_state.show_welcome:
    st.markdown(
        '<div class="welcome-shell"><div class="welcome-mark">✈</div><div class="welcome-title">Welcome to SafarAI Assistant</div><div class="welcome-copy">Your focused AI travel companion for planning trips, finding places and restaurants, checking weather, managing expenses, and making confident travel decisions.</div><div class="feature-list"><div class="feature-item"><strong>AI trip planning</strong><br><small>Personal recommendations and itinerary building.</small></div><div class="feature-item"><strong>Travel guidance</strong><br><small>Policies, visa information, and local etiquette.</small></div><div class="feature-item"><strong>Live utilities</strong><br><small>Weather and currency conversion for your trip.</small></div><div class="feature-item"><strong>Budget control</strong><br><small>Track expenses and remaining budget in PKR.</small></div></div></div>',
        unsafe_allow_html=True,
    )
    if st.button("Start planning", type="primary", use_container_width=True):
        st.session_state.show_welcome = False
        st.rerun()
    st.stop()

st.markdown('<div class="app-kicker">SafarAI</div><div class="app-title">Your intelligent travel companion</div><div class="app-subtitle">Plan with context, keep your budget visible, and make confident decisions on the move.</div>', unsafe_allow_html=True)

assistant_tab, budget_tab, weather_tab, currency_tab = st.tabs(["🤖 AI Assistant", "💰 Budget Tracker", "🌤️ Weather", "💱 Currency Converter"])

with assistant_tab:
    st.subheader("AI Travel Assistant")
    st.caption("Ask about policies, halal restaurants, attractions, weather, budget, or your itinerary.")
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    prompt = st.chat_input("Ask about your destination, budget, restaurants, places, weather, or travel policies...")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("🤖 Thinking..."):
                try:
                    payload = request_json("POST", CHAT_URL, json={"message": prompt, "thread_id": st.session_state.thread_id, "total_budget_pkr": st.session_state.metrics["total_budget"]})
                    st.session_state.thread_id = payload.get("thread_id", st.session_state.thread_id)
                    update_metrics(payload)
                    reply = payload.get("response", "I could not prepare a response.")
                except (requests.RequestException, RuntimeError) as error:
                    reply = format_error(error)
                st.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})

with budget_tab:
    st.subheader("💰 Budget Tracker")
    st.caption("This view is synchronized with the budget stored for your LangGraph conversation.")
    metrics = st.session_state.metrics
    total, spent, remaining = st.columns(3)
    total.metric("Total budget", f"{metrics['total_budget']:,.0f} PKR")
    spent.metric("Current spending", f"{metrics['spend']:,.0f} PKR")
    remaining.metric("Remaining", f"{metrics['remaining']:,.0f} PKR", delta=f"{metrics['remaining']:,.0f} PKR")
    if metrics["total_budget"]:
        st.progress(min(max(metrics["spend"] / metrics["total_budget"], 0.0), 1.0))
    if metrics["remaining"] < 0:
        st.error(f"Over budget by {abs(metrics['remaining']):,.0f} PKR")
    else:
        st.success(f"{(metrics['spend'] / metrics['total_budget'] * 100) if metrics['total_budget'] else 0:.0f}% of your budget allocated")
    with st.form("budget_form"):
        new_budget = st.number_input("Total budget (PKR)", min_value=0.0, value=metrics["total_budget"], step=10_000.0)
        save_budget = st.form_submit_button("Save budget", type="primary")
    if save_budget:
        try:
            update_metrics(request_json("PATCH", f"{STATE_URL}/{st.session_state.thread_id}/budget", json={"total_budget_pkr": new_budget}))
            st.success("Budget updated.")
            st.rerun()
        except (requests.RequestException, RuntimeError) as error:
            st.error(format_error(error))
    st.divider()
    st.subheader("Add expense")
    st.caption("Record a confirmed expense. It is deducted from the same backend budget state.")
    with st.form("expense_form"):
        expense_description = st.text_input("Expense name", placeholder="e.g. Dubai hotel")
        expense_amount = st.text_input("Amount (PKR)", placeholder="e.g. 60000")
        expense_category = st.text_input("Category", placeholder="e.g. Accommodation")
        add_expense = st.form_submit_button("Add expense", type="primary")
    if add_expense:
        try:
            parsed_expense = float(expense_amount.replace(",", "").strip())
            if parsed_expense <= 0 or not expense_description.strip():
                raise ValueError
        except (AttributeError, ValueError):
            st.error("Enter an expense name and a valid positive amount.")
        else:
            try:
                update_metrics(request_json("POST", f"{EXPENSE_URL}/{st.session_state.thread_id}/expenses", json={"expense_id": str(uuid.uuid4()), "description": expense_description, "amount_pkr": parsed_expense, "category": expense_category or "Other"}))
                st.success("Expense added and budget updated.")
                st.rerun()
            except (requests.RequestException, RuntimeError) as error:
                st.error(str(error) if isinstance(error, RuntimeError) else format_error(error))
    st.divider()
    st.subheader("Spending list")
    if metrics["itinerary"]:
        for item in metrics["itinerary"]:
            st.write(f"**{item.get('activity', 'Expense')}**  ·  {float(item.get('cost', 0)):,.0f} PKR")
    else:
        st.markdown('<div class="empty-state">No expenses recorded yet.</div>', unsafe_allow_html=True)
    st.divider()
    st.subheader("Expense breakdown")
    expenses = defaultdict(float)
    for item in metrics["itinerary"]:
        expenses[item.get("category", "Other")] += float(item.get("cost", 0))
    if expenses:
        for category, amount in expenses.items():
            st.write(f"**{category.title()}**  ·  {amount:,.0f} PKR")
    else:
        st.markdown('<div class="empty-state">No confirmed expenses yet. Add an activity through the Assistant.</div>', unsafe_allow_html=True)

with weather_tab:
    st.subheader("🌤️ Destination Weather")
    st.caption("Live conditions from the travel assistant's weather service.")
    with st.form("weather_form"):
        weather_city = st.text_input("City", placeholder="London")
        check_weather = st.form_submit_button("Check weather", type="primary")
    if check_weather:
        if not weather_city.strip():
            st.error("Enter a destination city.")
        else:
            with st.spinner("🌤️ Checking current conditions..."):
                try:
                    st.session_state.weather_result = request_json("POST", WEATHER_URL, json={"location": weather_city.strip()})
                except (requests.RequestException, RuntimeError) as error:
                    st.session_state.weather_result = {"error": format_error(error)}
    weather = st.session_state.weather_result
    if weather and weather.get("error"):
        st.error(weather["error"])
    elif weather:
        st.markdown(f"### {weather.get('location', weather_city)}, {weather.get('country', '')}")
        temperature, wind, rain = st.columns(3)
        temperature.metric("Temperature", f"{weather.get('temperature_c', '—')} °C")
        wind.metric("Wind", f"{weather.get('wind_speed_kmh', '—')} km/h")
        rain.metric("Precipitation", f"{weather.get('precipitation_mm', '—')} mm")
    else:
        st.markdown('<div class="empty-state">Search a city to see its current temperature, wind, and precipitation.</div>', unsafe_allow_html=True)

with currency_tab:
    st.subheader("💱 Currency Converter")
    st.caption("Use the latest available exchange rate for trip planning.")
    common_currencies = ["PKR", "AED", "USD", "GBP", "EUR", "JPY", "CAD"]
    with st.form("currency_form"):
        amount_text = st.text_input("Amount", placeholder="Enter amount")
        from_currency = st.selectbox("From", common_currencies, index=common_currencies.index("AED"))
        to_currency = st.selectbox("To", common_currencies, index=common_currencies.index("PKR"))
        convert = st.form_submit_button("Convert", type="primary")
    if convert:
        try:
            amount = float(amount_text.replace(",", "").strip())
            if amount < 0:
                raise ValueError
        except (AttributeError, ValueError):
            st.session_state.currency_result = {"error": "Enter a valid non-negative amount."}
        else:
            with st.spinner("💱 Fetching the latest exchange rate..."):
                try:
                    st.session_state.currency_result = request_json("POST", CURRENCY_URL, json={"amount": amount, "from_currency": from_currency, "to_currency": to_currency})
                except (requests.RequestException, RuntimeError) as error:
                    st.session_state.currency_result = {"error": format_error(error)}
    currency = st.session_state.currency_result
    if currency and currency.get("error"):
        st.error(currency["error"])
    elif currency:
        st.metric(f"{currency.get('amount', 0):,.2f} {currency.get('from_currency', from_currency)}", f"{currency.get('converted_amount', 0):,.2f} {currency.get('to_currency', to_currency)}")
        st.caption(f"Live rate: 1 {currency.get('from_currency', from_currency)} = {currency.get('rate', '—')} {currency.get('to_currency', to_currency)}")
    else:
        st.markdown('<div class="empty-state">Choose currencies and enter an amount to get a live conversion.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.caption(f"Conversation: {st.session_state.thread_id[:8]}…")
    if st.button("Reset conversation", use_container_width=True):
        reset_session()
        st.rerun()
