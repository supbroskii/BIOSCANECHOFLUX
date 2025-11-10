import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# -------------------------
# Page config
# -------------------------
st.set_page_config(page_title="BIOSCAN: EchoFlucs", page_icon="🐟", layout="wide")

# -------------------------
# Custom CSS (cards + header)
# -------------------------
st.markdown(
    """
    <style>
    .topbar { background: linear-gradient(180deg, #12324a 0%, #0d2740 100%) !important; }
    .kpi-pill {
        height:18px; width:220px; display:block; border-radius:12px; margin:0 auto 12px auto;
        background: linear-gradient(90deg,#0f2a44,#16314b);
        box-shadow: 0 6px 14px rgba(5,23,40,0.45);
    }
    .card-white {
        background: #ffffff;
        padding: 18px;
        border-radius: 14px;
        box-shadow: 0 6px 20px rgba(15,42,68,0.06);
        color: #0b2236;
        margin-bottom: 18px;
    }
    .stApp { background: #f6f8fb; }
    .sec-title { font-size:18px; font-weight:600; color:#0b2236; margin-bottom:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------
# Sidebar
# -------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "History", "Download Data"])

show_info = st.sidebar.checkbox("Show Device Info", value=True)

# -------------------------
# Google Sheets connection
# -------------------------
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_NAME = "FishData"  # change if your worksheet has a different name
    df = conn.read(worksheet=SHEET_NAME, usecols=list(range(5)), ttl=5)
    df = df.dropna(how="all")
except Exception as e:
    st.error(f"⚠️ Failed to load data: {e}")
    df = pd.DataFrame()

# -------------------------
# Data pre-processing
# -------------------------
if not df.empty:
    df.columns = ["Date", "Time", "Frequency", "Amplitude", "Classification"]
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date

    # Time parsing
    try:
        df["Time_parsed"] = pd.to_datetime(df["Time"], errors="coerce")
    except Exception:
        df["Time_parsed"] = pd.NaT

    df["Frequency"] = pd.to_numeric(df["Frequency"], errors="coerce")
    df["Amplitude"] = pd.to_numeric(df["Amplitude"], errors="coerce")

    def map_class(x):
        if pd.isna(x): 
            return "Unknown"
        s = str(x).strip().lower()
        if "pos" in s: 
            return "✅ Positive"
        if "neg" in s: 
            return "❌ Negative"
        return x

    df["Classification"] = df["Classification"].apply(map_class)

    # sample index for x-axis
    df = df.reset_index(drop=True)
    df["sample_idx"] = df.index + 1

    # --- define order for classification consistently everywhere ---
    order = ["✅ Positive", "❌ Negative", "Unknown"]

# -------------------------
# No data short-circuit
# -------------------------
if df.empty:
    st.title("BIOSCAN: EchoFlucs")
    if show_info:
        st.markdown(
            """
            <div class="card-white">
            <div class="sec-title">About the Device</div>
            <p>My device is a detection system that uses an <b>ESP32</b> with <b>piezo elements</b> to transmit and receive signals. 
            It generates a constant <b>200 Hz</b> tone while the receiver picks up the returning signal. FFT is used to compute dominant
            frequency & amplitude. Results are logged to Google Sheets.</p>
            </div>
            """, unsafe_allow_html=True
        )
    st.info("No data available. Check your Google Sheet (sheet name, permissions, or contents).")
    st.stop()

# -------------------------
# helper: KPI card HTML
# -------------------------
def kpi_card_html(title: str, value: str, pill_width="220px"):
    return f"""
    <div class="card-white">
      <div style="display:flex;justify-content:center;">
        <div class="kpi-pill" style="width:{pill_width};"></div>
      </div>
      <div style="text-align:left;">
        <div style="font-size:13px;color:#5b6b78;margin-bottom:6px;">{title}</div>
        <div style="font-size:34px;font-weight:700;color:#0b2236;">{value}</div>
      </div>
    </div>
    """

# -------------------------
# Device info
# -------------------------
st.title("BIOSCAN: EchoFlucs")
if show_info:
    st.markdown(
        """
        <div class="card-white">
        <div class="sec-title">About the Device</div>
        <p>My device is a detection system that uses an <b>ESP32 microcontroller</b> with <b>piezo elements</b> to transmit and receive signals.  
        It generates a constant <b>200 Hz tone</b> through the transmitter while the receiver picks up the returning signal.  
        Using <b>Fast Fourier Transform (FFT)</b>, the device processes the received signal to determine its dominant <b>frequency</b> and <b>amplitude</b>, 
        which are then classified into two statuses:</p>
        <ul>
            <li>✅ <b>Positive</b> → if the frequency fluctuates beyond a set threshold</li>
            <li>❌ <b>Negative</b> → if it remains stable</li>
        </ul>
        <p>Results are displayed on an LCD/LEDs and recorded locally (SD) and remotely (Google Sheets).</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -------------------------
# DASHBOARD page
# -------------------------
if page == "Dashboard":
    st.subheader("📊 General Panel (Latest Data)")

    latest = df.dropna(subset=["Frequency", "Amplitude"]).iloc[-1]

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        st.markdown(kpi_card_html("Latest Frequency (Hz)", f"{latest['Frequency']:.2f}"), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi_card_html("Latest Amplitude", f"{latest['Amplitude']:.2f}"), unsafe_allow_html=True)
    with c3:
        cls_text = latest["Classification"] if pd.notna(latest["Classification"]) else "Unknown"
        st.markdown(kpi_card_html("Latest Classification", f"{cls_text}"), unsafe_allow_html=True)

    left, right = st.columns([2,1])

    with left:
        st.markdown('<div class="card-white">', unsafe_allow_html=True)
        st.markdown('<div class="sec-title">📈 Frequency & Amplitude Trend</div>', unsafe_allow_html=True)

        x = df["sample_idx"]
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=x,
                y=df["Frequency"],
                name="Frequency",
                mode="lines",
                line=dict(color="#1f77b4"),
                fill="tozeroy",
                fillcolor="rgba(31,119,180,0.15)",
                hovertemplate="Sample %{x}<br>Frequency: %{y:.2f} Hz<extra></extra>"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=df["Amplitude"],
                name="Amplitude",
                mode="lines",
                line=dict(color="#ff7f0e", width=1.5),
                hovertemplate="Sample %{x}<br>Amplitude: %{y:.2f}<extra></extra>"
            )
        )

        fig.update_layout(
            template="simple_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=10, b=20, l=40, r=10),
            xaxis_title="Sample",
            yaxis_title="Reading",
            height=380
        )

        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card-white">', unsafe_allow_html=True)
        st.markdown('<div class="sec-title">📊 Classification Counts</div>', unsafe_allow_html=True)

        counts = df["Classification"].value_counts().reindex(order, fill_value=0).reset_index()
        counts.columns = ["Classification", "count"]

        bar = px.bar(
            counts,
            x="Classification",
            y="count",
            color="Classification",
            color_discrete_map={"✅ Positive": "seagreen", "❌ Negative": "crimson", "Unknown": "gray"},
            text="count",
        )
        bar.update_layout(showlegend=False, margin=dict(t=10, b=10, l=20, r=10), height=380)
        bar.update_traces(textposition="outside")
        st.plotly_chart(bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# HISTORY page
# -------------------------
elif page == "History":
    st.subheader("📅 Test History by Date")
    unique_dates = sorted([d for d in df["Date"].unique() if pd.notna(d)], reverse=True)
    selected_date = st.selectbox("Select a date to inspect", unique_dates)

    if selected_date:
        group = df[df["Date"] == selected_date].reset_index(drop=True)
        if group.empty:
            st.info("No records for that date.")
        else:
            avg_freq = group["Frequency"].mean()
            avg_amp = group["Amplitude"].mean()
            cls_counts = group["Classification"].value_counts().to_dict()

            c1, c2, c3 = st.columns([1,1,1])
            with c1:
                st.markdown(kpi_card_html("Avg Frequency (Hz)", f"{avg_freq:.2f}"), unsafe_allow_html=True)
            with c2:
                st.markdown(kpi_card_html("Avg Amplitude", f"{avg_amp:.2f}"), unsafe_allow_html=True)
            with c3:
                cls_summary = ", ".join([f"{k}: {v}" for k, v in cls_counts.items()])
                st.markdown(kpi_card_html("Classification Summary", cls_summary), unsafe_allow_html=True)

            # --- NEW BOX: Total Samples for the day ---
            total_samples = len(group)
            positive_count = cls_counts.get("✅ Positive", 0)
            negative_count = cls_counts.get("❌ Negative", 0)
            unknown_count = cls_counts.get("Unknown", 0)

            st.markdown(
                kpi_card_html(
                    f"📊 Total Samples for {selected_date}",
                    f"{total_samples} total — ✅ Positive: {positive_count}, ❌ Negative: {negative_count}, Unknown: {unknown_count}"
                ),
                unsafe_allow_html=True
            )

            left, right = st.columns([2,1])
            with left:
                st.markdown('<div class="card-white">', unsafe_allow_html=True)
                st.markdown(f'<div class="sec-title">📈 Combined Trend — {selected_date}</div>', unsafe_allow_html=True)
                x = group["sample_idx"]
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=x, y=group["Frequency"], name="Frequency", mode="lines",
                                          line=dict(color="#1f77b4"), fill="tozeroy", fillcolor="rgba(31,119,180,0.12)"))
                fig2.add_trace(go.Scatter(x=x, y=group["Amplitude"], name="Amplitude", mode="lines",
                                          line=dict(color="#ff7f0e", width=1.5)))
                fig2.update_layout(template="simple_white", margin=dict(t=10, b=20, l=40, r=10), height=360,
                                   xaxis_title="Sample", yaxis_title="Reading")
                st.plotly_chart(fig2, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with right:
                st.markdown('<div class="card-white">', unsafe_allow_html=True)
                st.markdown(f'<div class="sec-title">📊 Classification — {selected_date}</div>', unsafe_allow_html=True)
                counts = group["Classification"].value_counts().reindex(order, fill_value=0).reset_index()
                counts.columns = ["Classification", "count"]
                bar2 = px.bar(counts, x="Classification", y="count", color="Classification",
                              color_discrete_map={"✅ Positive": "seagreen", "❌ Negative": "crimson", "Unknown": "gray"},
                              text="count")
                bar2.update_layout(showlegend=False, margin=dict(t=10, b=10, l=20, r=10), height=360)
                bar2.update_traces(textposition="outside")
                st.plotly_chart(bar2, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card-white">', unsafe_allow_html=True)
            st.markdown('<div class="sec-title">📋 Raw Entries</div>', unsafe_allow_html=True)
            display_cols = ["Time", "Frequency", "Amplitude", "Classification"]
            st.dataframe(group[display_cols].reset_index(drop=True))
            st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# DOWNLOAD page
# -------------------------
elif page == "Download Data":
    st.subheader("💾 Download Data")
    st.markdown('<div class="card-white">', unsafe_allow_html=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Processed Data (All) as CSV", data=csv, file_name="bioscan_data.csv", mime="text/csv")

    st.markdown("---")
    st.write("Export by date:")
    unique_dates = sorted([d for d in df["Date"].unique() if pd.notna(d)], reverse=True)
    date_for_export = st.selectbox("Select date to export", ["(all)"] + [str(d) for d in unique_dates])
    if st.button("Prepare CSV for selected date"):
        if date_for_export == "(all)":
            data_to_export = df
        else:
            data_to_export = df[df["Date"].astype(str) == date_for_export]
        if data_to_export.empty:
            st.warning("No data for selected date.")
        else:
            csv2 = data_to_export.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV (filtered)", data=csv2, file_name=f"bioscan_{date_for_export}.csv", mime="text/csv")
    st.markdown('</div>', unsafe_allow_html=True)
