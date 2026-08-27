"""Generate data/eval/gold.yaml: 10 verified gold cases against the bundled sp500 data.
Every answer computed here, deterministically, from the shipped CSVs."""
import pandas as pd, yaml, os

import pathlib; R = str(pathlib.Path(__file__).resolve().parents[2])
sp = pd.read_csv(f'{R}/data/sp500/sp500_daily.csv', parse_dates=['Date'])
top = pd.read_csv(f'{R}/data/sp500/top20_daily.csv', parse_dates=['Date'])
etf = pd.read_csv(f'{R}/data/sp500/sector_etfs_daily.csv', parse_dates=['Date'])

cases = []
def add(qid, split, question, answer, unit, tol_pct, method):
    cases.append(dict(id=qid, split=split, question=question,
                      answer=round(float(answer), 4), unit=unit,
                      tolerance_pct=tol_pct, verified_method=method))

# 1. index close on a date
v = sp.loc[sp.Date == '2024-12-31', 'Close'].iloc[0]
add('G01', 'train', "What was the S&P 500 closing value on 2024-12-31 (sp500_daily.csv)?",
    v, 'index points', 0.1, 'exact lookup of Close where Date == 2024-12-31')

# 2. calendar-year return 2023
c22 = sp.loc[sp.Date <= '2022-12-31', 'Close'].iloc[-1]
c23 = sp.loc[sp.Date <= '2023-12-31', 'Close'].iloc[-1]
add('G02', 'train', "What was the S&P 500 total price return for calendar year 2023, in percent (last close of 2022 to last close of 2023)?",
    (c23/c22 - 1) * 100, 'percent', 1.0, 'last Close of 2022 vs last Close of 2023')

# 3. best top-20 ticker 2024
t = top.copy()
def yr_ret(g, y):
    prev = g.loc[g.Date <= f'{y-1}-12-31', 'Close']
    end = g.loc[g.Date <= f'{y}-12-31', 'Close']
    if prev.empty or end.empty: return None
    return (end.iloc[-1] / prev.iloc[-1] - 1) * 100
rets = {k: yr_ret(g.sort_values('Date'), 2024) for k, g in t.groupby('Ticker')}
best = max(rets, key=lambda k: rets[k])
add('G03', 'train', f"Among the 20 tickers in top20_daily.csv, which had the highest 2024 calendar-year price return, and what was that return in percent? (Answer value = the return; state the ticker in text.)",
    rets[best], 'percent', 2.0, f'per-ticker last-close 2023 vs 2024; winner {best}')
print('G03 winner:', best, round(rets[best],2))

# 4. worst sector 2022
e = etf.copy()
srets = {k: yr_ret(g.sort_values('Date'), 2022) for k, g in e.groupby('Sector')}
worst = min(srets, key=lambda k: srets[k])
add('G04', 'train', "Which sector ETF in sector_etfs_daily.csv had the lowest 2022 calendar-year price return, and what was it in percent? (Answer value = the return.)",
    srets[worst], 'percent', 2.0, f'per-sector last-close 2021 vs 2022; loser {worst}')
print('G04 loser:', worst, round(srets[worst],2))

# 5. max drawdown of index over full file
c = sp.sort_values('Date').Close
dd = (c / c.cummax() - 1).min() * 100
add('G05', 'train', "What was the maximum drawdown of the S&P 500 Close over the whole sp500_daily.csv file, in percent (peak-to-trough, negative number)?",
    dd, 'percent', 2.0, 'min of Close/cummax(Close) - 1')

# 6. average daily volume 2024 (billions)
v24 = sp[(sp.Date >= '2024-01-01') & (sp.Date <= '2024-12-31')].Volume.mean() / 1e9
add('G06', 'train', "What was the average daily S&P 500 volume in 2024, in billions of shares?",
    v24, 'billions of shares', 1.0, 'mean of Volume for 2024 rows / 1e9')

# 7. trading days count 2023
n = len(sp[(sp.Date >= '2023-01-01') & (sp.Date <= '2023-12-31')])
add('G07', 'test', "How many trading days does sp500_daily.csv contain in calendar year 2023?",
    n, 'days', 0.0, 'row count for 2023')

# 8. AAPL vs MSFT 2023 return spread
a = yr_ret(top[top.Ticker=='AAPL'].sort_values('Date'), 2023)
m = yr_ret(top[top.Ticker=='MSFT'].sort_values('Date'), 2023)
add('G08', 'test', "By how many percentage points did AAPL's 2023 calendar-year price return exceed MSFT's (negative if it trailed), using top20_daily.csv?",
    a - m, 'percentage points', 2.0, f'AAPL {a:.2f}% minus MSFT {m:.2f}%')

# 9. best single day for the index (percent gain)
sp2 = sp.sort_values('Date').copy()
sp2['ret'] = sp2.Close.pct_change() * 100
best_day = sp2.loc[sp2.ret.idxmax()]
add('G09', 'test', "What was the S&P 500's largest single-day percent gain in the file, and on what date? (Answer value = the percent gain.)",
    best_day.ret, 'percent', 2.0, f'max daily pct_change of Close; date {best_day.Date.date()}')
print('G09 date:', best_day.Date.date(), round(best_day.ret,2))

# 10. correlation XLK vs index daily returns
xlk = etf[etf.Ticker=='XLK'].sort_values('Date')[['Date','Close']].rename(columns={'Close':'xlk'})
j = sp2[['Date','Close']].merge(xlk, on='Date')
corr = j.Close.pct_change().corr(j.xlk.pct_change())
add('G10', 'test', "What is the Pearson correlation between daily percent returns of the S&P 500 (sp500_daily.csv Close) and the XLK technology ETF (sector_etfs_daily.csv Close), over all overlapping days?",
    corr, 'correlation', 3.0, 'corr of daily pct_change series on merged dates')

os.makedirs(f'{R}/data/eval', exist_ok=True)
doc = {
  'dataset': 'sp500 (bundled, data/sp500/)',
  'generated': '2026-08-27',
  'note': ('Public gold suite for the /eval skill. Every answer was computed deterministically '
           'from the bundled CSVs by the generator script (data/eval/make_gold.py). '
           'Splits: train cases may be inspected freely; test cases are for honest held-out runs.'),
  'grading': {'method': 'relative tolerance', 'rule': 'correct when |answer - gold| <= tolerance_pct% of |gold| (absolute match when tolerance_pct is 0)'},
  'cases': cases,
}
with open(f'{R}/data/eval/gold.yaml', 'w') as f:
    yaml.safe_dump(doc, f, sort_keys=False, width=100)
print('wrote', len(cases), 'cases')
for c in cases:
    print(c['id'], c['split'], c['answer'], c['unit'])
