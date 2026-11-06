"""Reusable visual components for exact calculations and statistical estimates."""
from html import escape

import plotly.graph_objects as go
import streamlit as st

PALETTE = ["#2DD4BF", "#60A5FA", "#C4B5FD", "#FBBF24"]


def apply_style():
    st.markdown("""
<style>
.block-container {max-width:1280px; padding-top:2.4rem; padding-bottom:4rem;}
[data-testid="stSidebar"] {border-right:1px solid #334155;}
h1 {letter-spacing:-.04em; font-weight:750 !important;}
h2,h3 {letter-spacing:-.025em;}
[data-testid="stMetric"] {background:#1F2937; border:1px solid #475569; border-radius:14px; padding:1rem 1.2rem;}
[data-testid="stMetricValue"] {overflow-wrap:anywhere;}
.eyebrow {color:#5EEAD4; letter-spacing:.15em; font-size:.75rem; font-weight:750;}
.hero {background:linear-gradient(115deg,#1e3a5f,#163b43); border:1px solid #3b5c76; border-radius:20px; padding:2rem; margin:1rem 0 1.5rem;}
.hero h2 {font-size:2.25rem; line-height:1.18; margin:.4rem 0 .9rem;}
.hero p,.card p {color:#d1d5db;}
.card {border:1px solid #475569; border-radius:16px; background:#1F2937; padding:1.3rem; min-height:265px; margin:.4rem 0 1rem;}
.card .tag {font-size:.72rem; color:#5eead4; letter-spacing:.08em;}
.subtle {color:#cbd5e1; font-size:.9rem;}
@media(max-width:600px){.block-container{padding-top:1.4rem;} .hero{padding:1.25rem;} .hero h2{font-size:1.9rem;} .card{min-height:0;} h1{font-size:2rem !important;}}
</style>""", unsafe_allow_html=True)


def header(kicker, title, subtitle):
    st.markdown(f'<div class="eyebrow">{escape(kicker)}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(subtitle)


def chart(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#e5e7eb", size=13),
                      margin=dict(l=20,r=20,t=55,b=45), colorway=PALETTE,
                      hoverlabel=dict(font_size=14), legend_title_text="")
    fig.update_xaxes(showgrid=False, automargin=True)
    fig.update_yaxes(gridcolor="#334155", automargin=True, zerolinecolor="#64748b")
    st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo":False})


def reliability_messages(result):
    for warning in result.get("warnings", []):
        st.warning(warning)
    reliability = result.get("reliability", {})
    if reliability:
        st.caption("Input support check: " + ("caution" if reliability.get("status") == "caution" else "no heuristic warning") +
                   ". Training-data similarity is a screening heuristic, not proof that an input is realistic or that a prediction is reliable.")


def prediction_result(result):
    """Render only artifact-bound evaluation, avoiding mismatch with a newer report."""
    stage = result["stage"].title()
    st.subheader(f"{stage} prediction result")
    st.caption("STATISTICAL ESTIMATE • Final Portuguese-course grade • Original scale: 0–20")
    nominal = result.get("nominal_coverage", .90)
    a,b = st.columns([1,1])
    a.metric("Estimated final grade", f"{result['prediction']:.1f} / 20")
    b.metric(f"{nominal:.0%} prediction interval", f"{result['lower']:.1f}–{result['upper']:.1f}")
    st.write(f"**Prediction stage:** {stage} · **Selected model:** {result['model_name']}")
    if result.get("active_features"):
        st.caption("Inputs used by the selected model: " + ", ".join(result["active_features"]) + ". Other profile fields do not affect this model’s point estimate.")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[result['lower'],result['upper']], y=[0,0], mode="lines",
        line=dict(color=PALETTE[0],width=12), name=f"{nominal:.0%} interval", hovertemplate="Grade %{x:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[result['prediction']], y=[0], mode="markers",
        marker=dict(color="#F9FAFB",size=15,line=dict(color="#111827",width=2)), name="Point estimate"))
    fig.update_layout(height=200, xaxis=dict(range=[0,20],title="Final grade (0–20)",dtick=5),
                      yaxis=dict(visible=False,range=[-1,1]),legend=dict(orientation="h"))
    chart(fig)
    evaluation = result.get("evaluation", {})
    test = evaluation.get("test", {})
    if test:
        st.markdown("**Measured error on the historical audit set**")
        a,b,c = st.columns(3)
        a.metric("MAE (grade points)",f"{test['mae']:.2f}")
        b.metric("RMSE (grade points)",f"{test['rmse']:.2f}")
        c.metric("R²",f"{test['r2']:.3f}")
        st.caption(f"Observed interval coverage: {test.get('coverage',0):.1%}. "
                   f"Nominal coverage: {nominal:.0%}. MAE is average absolute error; an individual error can be larger.")
        diagnostics = evaluation.get("interval_diagnostics", {})
        overall = diagnostics.get("overall", diagnostics)
        bounds = overall.get("coverage_95ci") or overall.get("wilson_interval") or overall.get("coverage_ci")
        if isinstance(bounds, (list,tuple)) and len(bounds)==2:
            st.caption(f"95% Wilson interval for observed coverage: {bounds[0]:.1%}–{bounds[1]:.1%}.")
    else:
        st.info("Evaluation metadata is unavailable for this artifact. Retrain before relying on these estimates.")
    if result.get("evaluation_context"):
        st.caption(result["evaluation_context"])
    if result["stage"] == "early":
        st.warning("Early estimates have limited predictive precision in this small historical dataset. A broad interval is a reason to plan with your actual assessment results rather than treat the point estimate as a target.")
    reliability_messages(result)
    st.info("The range is a split conformal prediction interval for a possible final outcome. Its nominal coverage is marginal under "
            "exchangeability with the historical calibration sample, not a personal guarantee. Coverage has not been validated for your institution.")
