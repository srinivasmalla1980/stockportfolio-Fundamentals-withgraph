# -*- coding: utf-8 -*-
import pandas as pd
import subprocess
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import mplcursors
from tabulate import tabulate
from IPython.display import display, Markdown

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

# ---------- Data Functions ----------

def get_quarterly_fundamentals(slug):
    url = f"https://www.screener.in/company/{slug}/consolidated/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Failed to fetch data for {slug}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("section", id="quarters")
    if not table:
        print(f"⚠️ Quarterly section not found for {slug}")
        return None

    headers = [th.text.strip() for th in table.find_all("th")]
    rows = table.find_all("tr")

    sales, net_profit, eps = [], [], []

    for row in rows:
        cols = [td.text.strip().replace(",", "") for td in row.find_all("td")]
        label = row.find("td").text.strip().lower() if row.find("td") else ""
        if "sales" in label and not sales:
            sales = cols
        elif "net profit" in label and not net_profit:
            net_profit = cols
        elif "eps" in label and not eps:
            eps = cols

    if not (sales and net_profit and eps):
        print(f"⚠️ Missing data for {slug.upper()}")
        return None

    df = pd.DataFrame({
        "Quarter": headers[1:],
        "Revenue (Cr)": sales[1:],
        "Net Profit (Cr)": net_profit[1:],
        "EPS": eps[1:]
    })

    return df

def get_stock_price(ticker):
    try:
        stock = yf.Ticker(ticker + ".NS")
        return stock.info['currentPrice']
    except:
        return "N/A"

# ---------- Plotting Functions ----------

def plot_and_save_fundamentals(df, ticker):
    df_plot = df.copy()
    df_plot[["Revenue (Cr)", "Net Profit (Cr)", "EPS"]] = df_plot[["Revenue (Cr)", "Net Profit (Cr)", "EPS"]].apply(pd.to_numeric, errors='coerce')

    x = range(len(df_plot["Quarter"]))
    bar_width = 0.35

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Bar plots for Revenue and Net Profit
    bars1 = ax1.bar([i - bar_width/2 for i in x], df_plot["Revenue (Cr)"], bar_width, label="Revenue (Cr)", color="#3498db", edgecolor="black")
    bars2 = ax1.bar([i + bar_width/2 for i in x], df_plot["Net Profit (Cr)"], bar_width, label="Net Profit (Cr)", color="#e74c3c", edgecolor="black")
    ax1.set_xlabel("Quarter")
    ax1.set_ylabel("₹ in Crores")
    ax1.set_xticks(x)
    ax1.set_xticklabels(df_plot["Quarter"], rotation=45, fontsize=10)
    ax1.tick_params(axis='y', labelsize=10)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    # EPS Line on right axis
    ax2 = ax1.twinx()
    eps_line, = ax2.plot(x, df_plot["EPS"], label="EPS", color="green", marker='o', linewidth=2)
    ax2.set_ylabel("EPS", fontsize=10)
    ax2.tick_params(axis='y', labelsize=10)

    # Combine Legends
    lines = [bars1, bars2, eps_line]
    labels = ["Revenue (Cr)", "Net Profit (Cr)", "EPS"]
    ax1.legend(lines, labels, loc="upper left", fontsize=10)

    plt.title(f"{ticker} – Quarterly Fundamentals (with EPS)", fontsize=14)
    plt.tight_layout()

    # Tooltips
    mplcursors.cursor([bars1, bars2, eps_line], hover=True)

    path = f"output/{ticker}_fundamentals.png"
    plt.savefig(path)
    plt.close()

def plot_and_save_ema_for_stock(ticker):
    stock = yf.Ticker(ticker + ".NS")
    hist = stock.history(period="1y")

    if hist.empty:
        print(f"⚠️ No historical data for {ticker}")
        return

    for period in [9, 20, 50, 100, 200]:
        hist[f'EMA_{period}'] = hist['Close'].ewm(span=period, adjust=False).mean()

    plt.figure(figsize=(12, 6))
    plt.plot(hist['Close'], label='Close Price', color='black', linewidth=2)
    plt.plot(hist['EMA_9'], label='EMA 9', linestyle='--')
    plt.plot(hist['EMA_20'], label='EMA 20', linestyle='--')
    plt.plot(hist['EMA_50'], label='EMA 50')
    plt.plot(hist['EMA_100'], label='EMA 100')
    plt.plot(hist['EMA_200'], label='EMA 200')

    plt.title(f"{ticker} – Close Price & EMA Trends (1 Year)", fontsize=14)
    plt.xlabel("Date")
    plt.ylabel("Price (₹)")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    mplcursors.cursor(hover=True)

    path = f"output/{ticker}_ema.png"
    plt.savefig(path)
    plt.close()

# ---------- Build and Save HTML Report ----------

def build_report():
    html = ["<html><head><title>📊 Daily Stock Report</title></head><body><h1>📈 Daily Stock Report</h1>"]

    # ✅ Read stock slugs and tickers from Excel file (e.g., stocks.xlsx with columns: slug, ticker)
    df_stocks = pd.read_excel("stocks.xlsx")  # Excel file must have columns: 'slug' and 'ticker'

    for _, row in df_stocks.iterrows():
        slug = row["slug"]
        ticker = row["ticker"]

        df = get_quarterly_fundamentals(slug)
        price = get_stock_price(ticker)
        stock_html = f"<h2>{ticker} — ₹{price}</h2>"

        if df is not None:
            plot_and_save_fundamentals(df, ticker)
            plot_and_save_ema_for_stock(ticker)
            stock_html += df.to_html(index=False)
            stock_html += f'<img src="output/{ticker}_fundamentals.png" style="width:90%;"><br>'
            stock_html += f'<img src="output/{ticker}_ema.png" style="width:90%;"><br>'

        html.append(stock_html)

    html.append("</body></html>")
    full_html_report = "\n".join(html)

    # ✅ Save HTML report to output folder
    with open("output/report.html", "w", encoding="utf-8") as f:
        f.write(full_html_report)

    print("✅ Report saved to output/report.html")
    
def build_report1():
    html = ["<html><head><title>📊 Daily Stock Report</title></head><body><h1>📈 Daily Stock Report</h1>"]
    stock_map = {"tcs": "TCS", "reliance": "RELIANCE", "infy": "INFY"}

    for slug, ticker in stock_map.items():
        df = get_quarterly_fundamentals(slug)
        price = get_stock_price(ticker)
        stock_html = f"<h2>{ticker} — ₹{price}</h2>"

        if df is not None:
            plot_and_save_fundamentals(df, ticker)
            plot_and_save_ema_for_stock(ticker)
            stock_html += df.to_html(index=False)
            stock_html += f'<img src="output/{ticker}_fundamentals.png" style="width:90%;"><br>'
            stock_html += f'<img src="output/{ticker}_ema.png" style="width:90%;"><br>'

        html.append(stock_html)

    html.append("</body></html>")
    full_html_report = "\n".join(html)

    # ✅ Save HTML report to output folder
    with open("output/report.html", "w", encoding="utf-8") as f:
        f.write(full_html_report)

    print("✅ Report saved to output/report.html")

# ---------- Run Script ----------
if __name__ == "__main__":
    build_report()
