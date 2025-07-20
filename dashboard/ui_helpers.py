import streamlit as st


def format_percentage(value):
    """
    Formats a numeric value as a percentage string with a sign and an arrow.
    """
    if value is None:
        return ""

    arrow = "↑" if value >= 0 else "↓"
    color = "green" if value >= 0 else "red"
    return f"<span style='color:{color}'>{arrow} {value:.1f}%</span>"


def display_header():
    """
    Displays the main header of the dashboard.
    """
    st.title("Keyword Category Trend Monitor")


def display_section_title(title):
    """
    Displays a section title.
    """
    st.header(title)