"""Shared chart styles and prediction displays."""
import plotly.graph_objects as go
import streamlit as st

PALETTE = ["#2DD4BF", "#60A5FA", "#C4B5FD", "#FBBF24"]


def apply_style():
    st.markdown("""
<style>
.block-container {max-width:1200px; padding-top:2.6rem; padding-bottom:3rem;}
[data-testid="stSidebar"] {border-right:1px solid #334155;}
h1,h2,h3 {letter-spacing:-.025em;}
[data-testid="stMetric"] {
    background:#1F2937; border:1px solid #475569; border-radius:.6rem; padding:.75rem 1rem;
}
[data-testid="stMetricValue"] {overflow-wrap:anywhere;}
@media (max-width:640px) {
    .block-container {padding:2rem 1rem;}
    h1 {font-size:1.95rem !important;}
    [data-testid="stMetric"] {padding:.65rem .8rem;}
}
</style>""", unsafe_allow_html=True)


def chart(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#e5e7eb", size=13),
                      margin=dict(l=16, r=16, t=55, b=45), colorway=PALETTE,
                      hoverlabel=dict(font_size=14), legend=dict(orientation="h", y=-0.25),
                      legend_title_text="")
    fig.update_xaxes(showgrid=False, automargin=True)
    fig.update_yaxes(gridcolor="#334155", automargin=True, zerolinecolor="#64748b")
    st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo":False})


def reliability_messages(result):
    for warning in result.get("warnings", []):
        st.warning(warning)
    reliability = result.get("reliability", {})
    if reliability:
        st.caption("Training data check — " + ("caution" if reliability.get("status") == "caution" else "no unusual input flagged") +
                   ". This check flags unusual inputs. It cannot establish whether the estimate is reliable.")


def prediction_result(result):
    """Show the historical evaluation bundled with this model."""
    stage = result["stage"].title()
    st.subheader(f"{stage} prediction result")
    st.caption("Estimated final grade for the Portuguese course on a 0–20 scale.")
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
        st.info("Historical error and coverage metrics are unavailable for this estimate.")
    if result.get("evaluation_context"):
        st.caption(result["evaluation_context"])
    if result["stage"] == "early":
        st.warning("Early estimates have wide ranges and can overestimate low grades. Use your recorded assessment marks to plan your course grade.")
    reliability_messages(result)
    st.info("The interval targets average coverage across records similar to the calibration sample. "
            "Coverage for your institution has not been measured.")
