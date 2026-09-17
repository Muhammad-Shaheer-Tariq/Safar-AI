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

st.set_page_config(
    page_title="SafarAI Travel Agent",
    page_icon="✈️",
    layout="wide"
)


def initialize_session() -> None:
    defaults = {
        "thread_id": str(uuid.uuid4()),
        "show_welcome": True,
        "chat_history": [],
        "metrics": {
            "total_budget": DEFAULT_BUDGET,
            "spend": 0.0,
            "remaining": DEFAULT_BUDGET,
            "itinerary": []
        },
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
        raise RuntimeError(
            payload.get(
                "detail",
                "The backend could not complete that request."
            )
        )

    return payload


def update_metrics(payload: dict) -> None:
    metrics = st.session_state.metrics

    metrics["total_budget"] = float(
        payload.get("total_budget_pkr", metrics["total_budget"])
    )

    metrics["spend"] = float(
        payload.get("current_spend", metrics["spend"])
    )

    metrics["remaining"] = float(
        payload.get("remaining_budget", metrics["remaining"])
    )

    metrics["itinerary"] = payload.get(
        "itinerary",
        metrics["itinerary"]
    )


def sync_thread_state() -> None:
    try:
        payload = request_json(
            "GET",
            f"{STATE_URL}/{st.session_state.thread_id}"
        )

        if payload.get("initialized"):
            update_metrics(payload)

    except (requests.RequestException, RuntimeError):
        pass


def reset_session() -> None:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.chat_history = []

    st.session_state.metrics = {
        "total_budget": DEFAULT_BUDGET,
        "spend": 0.0,
        "remaining": DEFAULT_BUDGET,
        "itinerary": []
    }

    st.session_state.weather_result = None
    st.session_state.currency_result = None


def format_error(error: Exception) -> str:
    return "The backend is unavailable right now. Please try again shortly."


initialize_session()
sync_thread_state()


# =========================
# UI STYLING
# =========================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');

    :root {
        --olive: #6b7a3f;
        --dark-olive: #3f4d22;
        --olive-pale: #f6f8f0;
        --olive-soft: #eaeeda;
        --olive-mid: #dbe3c6;
        --line: #d9dfc8;
        --ink: #262f1c;
        --muted: #6a715f;
        --white: #ffffff;
        --cream: #fbfaf5;
        --gold: #b8923f;
        --danger: #b3452f;
        --success: #4f7a3d;
        --shadow-sm: 0 1px 3px rgba(63, 77, 34, 0.08);
        --shadow-md: 0 6px 20px rgba(63, 77, 34, 0.10);
        --radius: 12px;
    }

    /* Hide Streamlit chrome: menu, footer, deploy/GitHub toolbar */
    #MainMenu {visibility: hidden; height: 0;}
    footer {visibility: hidden; height: 0;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    a[href*="github.com"] {display: none !important;}

    html,
    body,
    [data-testid="stAppViewContainer"],
    [data-testid="stApp"] {
        background: var(--cream);
        color: var(--ink);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    [data-testid="stHeader"] {
        background: transparent;
        height: 0;
    }

    .block-container {
        max-width: 1180px;
        padding-top: 0.6rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3, h4, label, p {
        color: var(--ink);
        font-family: 'Inter', sans-serif;
    }

    [data-testid="stCaptionContainer"] p {
        color: var(--muted);
    }


    /* =========================
       SAFARAI BRAND HEADER
       ========================= */

    .brand-header {
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 1.6rem 0 1.3rem;
        margin-bottom: 1.8rem;
        position: relative;
    }

    .brand-name {
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(90deg, var(--dark-olive), var(--olive));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.6rem;
        font-weight: 800;
        line-height: 1.1;
        letter-spacing: -1px;
    }

    .brand-tagline {
        color: var(--muted);
        font-size: 0.95rem;
        margin-top: 0.5rem;
        font-weight: 500;
    }

    .brand-underline {
        width: 96px;
        height: 4px;
        margin-top: 1rem;
        border-radius: 4px;
        background: linear-gradient(90deg, var(--olive), var(--gold));
    }


    /* =========================
       WELCOME PAGE
       ========================= */

    .welcome-shell {
        max-width: 880px;
        margin: 5vh auto 0;
        padding: 3.6rem 3.2rem;
        text-align: center;
        background: var(--white);
        border: 1px solid var(--line);
        border-radius: 20px;
        box-shadow: var(--shadow-md);
    }

    .welcome-mark {
        width: 60px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 1.2rem;
        background: linear-gradient(135deg, var(--olive), var(--dark-olive));
        color: var(--white);
        border-radius: 16px;
        font-size: 1.6rem;
        box-shadow: var(--shadow-sm);
    }

    .welcome-title {
        font-family: 'Poppins', sans-serif;
        color: var(--dark-olive);
        font-size: clamp(2.1rem, 5vw, 3.2rem);
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 1rem;
    }

    .welcome-copy {
        color: var(--muted);
        font-size: 1.03rem;
        line-height: 1.75;
        max-width: 680px;
        margin: 0 auto 1.6rem;
    }

    .welcome-note {
        color: var(--ink);
        font-size: 0.92rem;
        line-height: 1.65;
        max-width: 660px;
        margin: 0 auto 2.2rem;
        background: var(--olive-pale);
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 0.9rem 1.1rem;
    }

    .feature-list {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.9rem;
        text-align: left;
        max-width: 700px;
        margin: 0 auto 2.2rem;
    }

    .feature-item {
        background: var(--olive-pale);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 1.05rem 1.15rem;
        line-height: 1.5;
        transition: box-shadow 0.15s ease, transform 0.15s ease;
    }

    .feature-item:hover {
        box-shadow: var(--shadow-sm);
        transform: translateY(-2px);
    }

    .feature-item strong {
        color: var(--dark-olive);
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
    }

    .feature-item small {
        color: var(--muted);
    }


    /* =========================
       TABS
       ========================= */

    div[data-baseweb="tab-list"] {
        gap: 0.4rem;
        border-bottom: 1px solid var(--line);
    }

    button[data-baseweb="tab"] {
        color: var(--muted);
        font-weight: 600;
        font-size: 0.95rem;
        padding: 0.75rem 1.1rem;
        border-radius: 8px 8px 0 0;
        transition: background 0.15s ease, color 0.15s ease;
    }

    button[data-baseweb="tab"]:hover {
        background: var(--olive-pale);
        color: var(--dark-olive);
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--dark-olive);
        background: var(--olive-soft);
        border-bottom-color: var(--olive);
    }


    /* =========================
       CHAT MESSAGES
       ========================= */

    [data-testid="stChatMessage"] {
        background: var(--white);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        margin-bottom: 0.8rem;
        padding: 0.4rem 0.2rem;
        box-shadow: var(--shadow-sm);
    }

    [data-testid="stChatMessage"]
    [data-testid="stMarkdownContainer"],
    [data-testid="stChatMessage"]
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stChatMessage"]
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stChatMessage"]
    [data-testid="stMarkdownContainer"] strong,
    [data-testid="stChatMessage"]
    [data-testid="stMarkdownContainer"] em,
    [data-testid="stChatMessage"]
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stChatMessage"]
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stChatMessage"]
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stChatMessage"]
    [data-testid="stMarkdownContainer"] blockquote,
    [data-testid="stChatMessage"]
    [data-testid="stMarkdownContainer"] a {
        color: var(--ink) !important;
    }

    [data-testid="stChatMessage"]
    [data-testid="stMarkdownContainer"] code {
        color: var(--dark-olive) !important;
        background: var(--olive-pale);
    }


    /* =========================
       CHAT INPUT
       ========================= */

    [data-testid="stChatInput"] {
        background: var(--white) !important;
        border: 1.5px solid var(--olive) !important;
        border-radius: 14px !important;
        box-shadow: var(--shadow-sm);
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: var(--dark-olive) !important;
        box-shadow: 0 0 0 3px rgba(107, 122, 63, 0.18);
    }

    [data-testid="stChatInput"] textarea,
    [data-testid="stChatInput"] input {
        color: var(--ink) !important;
        background: var(--white) !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    [data-testid="stChatInput"]
    textarea::placeholder,
    [data-testid="stChatInput"]
    input::placeholder {
        color: #7c8570 !important;
        opacity: 1 !important;
        -webkit-text-fill-color: #7c8570 !important;
    }


    /* =========================
       OTHER INPUTS
       ========================= */

    input,
    textarea,
    [data-baseweb="select"] input,
    [data-baseweb="select"] > div {
        color: var(--ink) !important;
        background: var(--white) !important;
        border-color: var(--line) !important;
        border-radius: 8px !important;
        -webkit-text-fill-color: var(--ink) !important;
    }

    input:focus,
    textarea:focus {
        border-color: var(--olive) !important;
        box-shadow: 0 0 0 2px rgba(107, 122, 63, 0.15) !important;
    }

    input::placeholder,
    textarea::placeholder,
    [data-baseweb="select"]
    input::placeholder {
        color: #7c8570 !important;
        opacity: 1 !important;
        -webkit-text-fill-color: #7c8570 !important;
    }


    /* =========================
       BUTTONS
       ========================= */

    button[kind="primary"] {
        background: var(--olive);
        border-color: var(--olive);
        color: var(--white);
        border-radius: 10px;
        font-weight: 600;
        transition: background 0.15s ease, box-shadow 0.15s ease, transform 0.1s ease;
    }

    button[kind="primary"]:hover {
        background: var(--dark-olive);
        border-color: var(--dark-olive);
        box-shadow: var(--shadow-sm);
        transform: translateY(-1px);
    }

    button[kind="secondary"] {
        border-radius: 10px;
        font-weight: 600;
    }


    /* =========================
       METRICS
       ========================= */

    [data-testid="stMetric"] {
        background: var(--white);
        border: 1px solid var(--line);
        border-top: 3px solid var(--olive);
        padding: 1.05rem 1.1rem;
        border-radius: var(--radius);
        box-shadow: var(--shadow-sm);
    }

    [data-testid="stMetricValue"] {
        color: var(--dark-olive);
        font-family: 'Poppins', sans-serif;
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted);
        font-weight: 600;
    }

    [data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, var(--olive), var(--gold));
    }


    /* =========================
       EMPTY STATES
       ========================= */

    .empty-state {
        background: var(--olive-pale);
        border: 1px dashed #c5cfaa;
        border-radius: var(--radius);
        padding: 1.3rem;
        color: var(--muted);
        text-align: center;
        font-size: 0.92rem;
    }


    /* =========================
       FORMS / CONTAINERS
       ========================= */

    [data-testid="stForm"] {
        background: var(--white);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        padding: 1.2rem;
        box-shadow: var(--shadow-sm);
    }

    hr, [data-testid="stDivider"] {
        border-color: var(--line) !important;
    }


    /* =========================
       MOBILE
       ========================= */

    @media (max-width: 720px) {

        .block-container {
            padding: 0.8rem 0.9rem 2rem;
        }

        .brand-header {
            padding: 1.1rem 0 1rem;
        }

        .brand-name {
            font-size: 1.7rem;
        }

        .welcome-shell {
            margin-top: 3vh;
            padding: 2.2rem 1.2rem;
        }

        .welcome-title {
            font-size: 2rem;
        }

        .feature-list {
            grid-template-columns: 1fr;
        }

        div[data-baseweb="tab-list"] {
            overflow-x: auto;
            flex-wrap: nowrap;
        }

        button[data-baseweb="tab"] {
            min-width: max-content;
            padding-left: 0.65rem;
            padding-right: 0.65rem;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# WELCOME SCREEN
# =========================

if st.session_state.show_welcome:

    st.markdown(
        '<div class="welcome-shell">'
        '<div class="welcome-mark">✈</div>'
        '<div class="welcome-title">Welcome to SafarAI</div>'

        '<div class="welcome-copy">'
        'SafarAI is your intelligent travel assistant for planning and '
        'managing trips in one place. Ask questions naturally, explore '
        'destinations and restaurants, check live weather and currency '
        'rates, build your itinerary, and keep your travel spending '
        'under control.'
        '</div>'

        '<div class="welcome-note">'
        'Start with a destination, a budget, or a simple travel question. '
        'SafarAI keeps the conversation connected so your plans, budget, '
        'and itinerary can stay together throughout your trip.'
        '</div>'

        '<div class="feature-list">'

        '<div class="feature-item">'
        '<strong>AI trip planning</strong><br>'
        '<small>Plan destinations, activities, routes, and itineraries '
        'through conversation.</small>'
        '</div>'

        '<div class="feature-item">'
        '<strong>Travel guidance</strong><br>'
        '<small>Get help with travel policies, local information, '
        'and destination questions.</small>'
        '</div>'

        '<div class="feature-item">'
        '<strong>Live travel utilities</strong><br>'
        '<small>Check current weather conditions and convert currencies '
        'for your trip.</small>'
        '</div>'

        '<div class="feature-item">'
        '<strong>Budget management</strong><br>'
        '<small>Set your budget, record expenses, and monitor what '
        'remains in PKR.</small>'
        '</div>'

        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button(
        "Start planning",
        type="primary",
        use_container_width=True
    ):
        st.session_state.show_welcome = False
        st.rerun()

    st.stop()


# =========================
# BRAND HEADER
# =========================

# SafarAI header
st.markdown(
    """
    <div class="brand-header">
        <div class="brand-name">SafarAI</div>
        <div class="brand-tagline">
            Intelligent travel planning, live travel tools, and budget control.
        </div>
        <div class="brand-underline"></div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================
# MAIN TABS
# =========================

assistant_tab, budget_tab, weather_tab, currency_tab = st.tabs(
    [
        "🤖 AI Assistant",
        "💰 Budget Tracker",
        "🌤️ Weather",
        "💱 Currency Converter"
    ]
)


# =========================
# AI ASSISTANT
# =========================

with assistant_tab:

    st.subheader("AI Travel Assistant")

    st.caption(
        "Ask about destinations, halal restaurants, attractions, weather, "
        "your budget, or your itinerary — all in one conversation."
    )

    for message in st.session_state.chat_history:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input(
        "Ask SafarAI — e.g. \"Plan a 5-day trip to Istanbul under 150,000 PKR\""
    )

    if prompt:

        st.session_state.chat_history.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):

            with st.spinner("🤖 Thinking..."):

                try:

                    payload = request_json(
                        "POST",
                        CHAT_URL,
                        json={
                            "message": prompt,
                            "thread_id": st.session_state.thread_id,
                            "total_budget_pkr": st.session_state.metrics[
                                "total_budget"
                            ]
                        }
                    )

                    st.session_state.thread_id = payload.get(
                        "thread_id",
                        st.session_state.thread_id
                    )

                    update_metrics(payload)

                    reply = payload.get(
                        "response",
                        "I could not prepare a response."
                    )

                except (
                    requests.RequestException,
                    RuntimeError
                ) as error:

                    reply = format_error(error)

                st.markdown(reply)

                st.session_state.chat_history.append(
                    {
                        "role": "assistant",
                        "content": reply
                    }
                )


# =========================
# BUDGET TRACKER
# =========================

with budget_tab:

    st.subheader("💰 Budget Tracker")

    st.caption(
        "This view is synchronized with the budget stored for "
        "your current SafarAI conversation."
    )

    metrics = st.session_state.metrics

    total, spent, remaining = st.columns(3)

    total.metric(
        "Total budget",
        f"{metrics['total_budget']:,.0f} PKR"
    )

    spent.metric(
        "Current spending",
        f"{metrics['spend']:,.0f} PKR"
    )

    remaining.metric(
        "Remaining",
        f"{metrics['remaining']:,.0f} PKR",
        delta=f"{metrics['remaining']:,.0f} PKR"
    )

    if metrics["total_budget"]:

        st.progress(
            min(
                max(
                    metrics["spend"] /
                    metrics["total_budget"],
                    0.0
                ),
                1.0
            )
        )

    if metrics["remaining"] < 0:

        st.error(
            f"Over budget by "
            f"{abs(metrics['remaining']):,.0f} PKR"
        )

    else:

        st.success(
            f"{(metrics['spend'] / metrics['total_budget'] * 100) if metrics['total_budget'] else 0:.0f}% "
            "of your budget allocated"
        )

    with st.form("budget_form"):

        new_budget = st.number_input(
            "Total budget (PKR)",
            min_value=0.0,
            value=metrics["total_budget"],
            step=10_000.0
        )

        save_budget = st.form_submit_button(
            "Save budget",
            type="primary"
        )

    if save_budget:

        try:

            update_metrics(
                request_json(
                    "PATCH",
                    f"{STATE_URL}/{st.session_state.thread_id}/budget",
                    json={
                        "total_budget_pkr": new_budget
                    }
                )
            )

            st.success("Budget updated.")

            st.rerun()

        except (
            requests.RequestException,
            RuntimeError
        ) as error:

            st.error(format_error(error))


    st.divider()

    st.subheader("Add expense")

    st.caption(
        "Record a confirmed expense. It is deducted from "
        "the same backend budget state."
    )

    with st.form("expense_form"):

        expense_description = st.text_input(
            "Expense name",
            placeholder="e.g. Dubai hotel — 3 nights"
        )

        expense_amount = st.text_input(
            "Amount (PKR)",
            placeholder="e.g. 60,000"
        )

        expense_category = st.text_input(
            "Category",
            placeholder="e.g. Accommodation, Food, Transport"
        )

        add_expense = st.form_submit_button(
            "Add expense",
            type="primary"
        )

    if add_expense:

        try:

            parsed_expense = float(
                expense_amount.replace(",", "").strip()
            )

            if (
                parsed_expense <= 0
                or not expense_description.strip()
            ):
                raise ValueError

        except (
            AttributeError,
            ValueError
        ):

            st.error(
                "Enter an expense name and a valid positive amount."
            )

        else:

            try:

                update_metrics(
                    request_json(
                        "POST",
                        f"{EXPENSE_URL}/{st.session_state.thread_id}/expenses",
                        json={
                            "expense_id": str(uuid.uuid4()),
                            "description": expense_description,
                            "amount_pkr": parsed_expense,
                            "category": expense_category or "Other"
                        }
                    )
                )

                st.success(
                    "Expense added and budget updated."
                )

                st.rerun()

            except (
                requests.RequestException,
                RuntimeError
            ) as error:

                st.error(
                    str(error)
                    if isinstance(error, RuntimeError)
                    else format_error(error)
                )


    st.divider()

    st.subheader("Spending list")

    if metrics["itinerary"]:

        for item in metrics["itinerary"]:

            st.write(
                f"**{item.get('activity', 'Expense')}**  ·  "
                f"{float(item.get('cost', 0)):,.0f} PKR"
            )

    else:

        st.markdown(
            '<div class="empty-state">'
            'No expenses recorded yet. Add one above to see it here.'
            '</div>',
            unsafe_allow_html=True
        )


    st.divider()

    st.subheader("Expense breakdown")

    expenses = defaultdict(float)

    for item in metrics["itinerary"]:

        expenses[
            item.get("category", "Other")
        ] += float(
            item.get("cost", 0)
        )

    if expenses:

        for category, amount in expenses.items():

            st.write(
                f"**{category.title()}**  ·  "
                f"{amount:,.0f} PKR"
            )

    else:

        st.markdown(
            '<div class="empty-state">'
            'No confirmed expenses yet. Add an activity through '
            'the Assistant tab or the form above.'
            '</div>',
            unsafe_allow_html=True
        )


# =========================
# WEATHER
# =========================

with weather_tab:

    st.subheader("🌤️ Destination Weather")

    st.caption(
        "Live conditions from SafarAI's weather service."
    )

    with st.form("weather_form"):

        weather_city = st.text_input(
            "City",
            placeholder="e.g. Istanbul, Dubai, London"
        )

        check_weather = st.form_submit_button(
            "Check weather",
            type="primary"
        )

    if check_weather:

        if not weather_city.strip():

            st.error("Enter a destination city.")

        else:

            with st.spinner(
                "🌤️ Checking current conditions..."
            ):

                try:

                    st.session_state.weather_result = request_json(
                        "POST",
                        WEATHER_URL,
                        json={
                            "location": weather_city.strip()
                        }
                    )

                except (
                    requests.RequestException,
                    RuntimeError
                ) as error:

                    st.session_state.weather_result = {
                        "error": format_error(error)
                    }

    weather = st.session_state.weather_result

    if weather and weather.get("error"):

        st.error(weather["error"])

    elif weather:

        st.markdown(
            f"### {weather.get('location', weather_city)}, "
            f"{weather.get('country', '')}"
        )

        temperature, wind, rain = st.columns(3)

        temperature.metric(
            "Temperature",
            f"{weather.get('temperature_c', '—')} °C"
        )

        wind.metric(
            "Wind",
            f"{weather.get('wind_speed_kmh', '—')} km/h"
        )

        rain.metric(
            "Precipitation",
            f"{weather.get('precipitation_mm', '—')} mm"
        )

    else:

        st.markdown(
            '<div class="empty-state">'
            'Search a city to see its current temperature, '
            'wind, and precipitation.'
            '</div>',
            unsafe_allow_html=True
        )


# =========================
# CURRENCY CONVERTER
# =========================

with currency_tab:

    st.subheader("💱 Currency Converter")

    st.caption(
        "Use the latest available exchange rate for trip planning."
    )

    common_currencies = [
        "PKR",
        "AED",
        "USD",
        "GBP",
        "EUR",
        "JPY",
        "CAD"
    ]

    with st.form("currency_form"):

        amount_text = st.text_input(
            "Amount",
            placeholder="e.g. 1,000"
        )

        from_currency = st.selectbox(
            "From",
            common_currencies,
            index=common_currencies.index("AED")
        )

        to_currency = st.selectbox(
            "To",
            common_currencies,
            index=common_currencies.index("PKR")
        )

        convert = st.form_submit_button(
            "Convert",
            type="primary"
        )

    if convert:

        try:

            amount = float(
                amount_text.replace(",", "").strip()
            )

            if amount < 0:
                raise ValueError

        except (
            AttributeError,
            ValueError
        ):

            st.session_state.currency_result = {
                "error": "Enter a valid non-negative amount."
            }

        else:

            with st.spinner(
                "💱 Fetching the latest exchange rate..."
            ):

                try:

                    st.session_state.currency_result = request_json(
                        "POST",
                        CURRENCY_URL,
                        json={
                            "amount": amount,
                            "from_currency": from_currency,
                            "to_currency": to_currency
                        }
                    )

                except (
                    requests.RequestException,
                    RuntimeError
                ) as error:

                    st.session_state.currency_result = {
                        "error": format_error(error)
                    }

    currency = st.session_state.currency_result

    if currency and currency.get("error"):

        st.error(currency["error"])

    elif currency:

        st.metric(
            f"{currency.get('amount', 0):,.2f} "
            f"{currency.get('from_currency', from_currency)}",

            f"{currency.get('converted_amount', 0):,.2f} "
            f"{currency.get('to_currency', to_currency)}"
        )

        st.caption(
            f"Live rate: 1 "
            f"{currency.get('from_currency', from_currency)} = "
            f"{currency.get('rate', '—')} "
            f"{currency.get('to_currency', to_currency)}"
        )

    else:

        st.markdown(
            '<div class="empty-state">'
            'Choose currencies and enter an amount to get a live '
            'conversion.'
            '</div>',
            unsafe_allow_html=True
        )