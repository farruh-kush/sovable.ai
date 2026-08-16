from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

OUT = Path('/home/ubuntu/sovereign_ai_research')

weights = {
    'Sovereignty and residency control': 0.25,
    'Time to pilot': 0.15,
    'Feature coverage': 0.15,
    'Cost predictability': 0.10,
    'Customization for Uzbekistan': 0.15,
    'Operational risk': 0.10,
    'Vendor independence': 0.10,
}

scores = {
    'Ready to buy': {
        'Sovereignty and residency control': 3,
        'Time to pilot': 5,
        'Feature coverage': 5,
        'Cost predictability': 3,
        'Customization for Uzbekistan': 3,
        'Operational risk': 4,
        'Vendor independence': 1,
    },
    'Fully open-source': {
        'Sovereignty and residency control': 5,
        'Time to pilot': 3,
        'Feature coverage': 3,
        'Cost predictability': 3,
        'Customization for Uzbekistan': 4,
        'Operational risk': 2,
        'Vendor independence': 5,
    },
    'Open-source + own development': {
        'Sovereignty and residency control': 5,
        'Time to pilot': 4,
        'Feature coverage': 4,
        'Cost predictability': 3,
        'Customization for Uzbekistan': 5,
        'Operational risk': 3,
        'Vendor independence': 5,
    },
    'Own from scratch': {
        'Sovereignty and residency control': 5,
        'Time to pilot': 2,
        'Feature coverage': 3,
        'Cost predictability': 1,
        'Customization for Uzbekistan': 5,
        'Operational risk': 1,
        'Vendor independence': 5,
    },
}

costs = [
    {
        'option': 'Ready to buy',
        'pilot_setup_low': 10000,
        'pilot_setup_high': 75000,
        'pilot_monthly_low': 2000,
        'pilot_monthly_high': 15000,
        'production_setup_low': 50000,
        'production_setup_high': 250000,
        'production_monthly_low': 8000,
        'production_monthly_high': 35000,
        'pilot_months': '1–3',
        'production_months': '3–8',
    },
    {
        'option': 'Fully open-source',
        'pilot_setup_low': 60000,
        'pilot_setup_high': 180000,
        'pilot_monthly_low': 8000,
        'pilot_monthly_high': 30000,
        'production_setup_low': 180000,
        'production_setup_high': 500000,
        'production_monthly_low': 20000,
        'production_monthly_high': 70000,
        'pilot_months': '3–6',
        'production_months': '6–12',
    },
    {
        'option': 'Open-source + own development',
        'pilot_setup_low': 120000,
        'pilot_setup_high': 300000,
        'pilot_monthly_low': 12000,
        'pilot_monthly_high': 40000,
        'production_setup_low': 300000,
        'production_setup_high': 900000,
        'production_monthly_low': 30000,
        'production_monthly_high': 100000,
        'pilot_months': '4–8',
        'production_months': '9–18',
    },
    {
        'option': 'Own from scratch',
        'pilot_setup_low': 350000,
        'pilot_setup_high': 650000,
        'pilot_monthly_low': 20000,
        'pilot_monthly_high': 60000,
        'production_setup_low': 750000,
        'production_setup_high': 2000000,
        'production_monthly_low': 50000,
        'production_monthly_high': 180000,
        'pilot_months': '9–15',
        'production_months': '18–30',
    },
]

weighted_rows = []
for option, dimensions in scores.items():
    weighted = sum(dimensions[k] * weights[k] for k in weights)
    row = {'option': option, 'weighted_score_5': round(weighted, 2), 'weighted_score_100': round(weighted * 20, 1)}
    row.update({k: dimensions[k] for k in weights})
    weighted_rows.append(row)

with (OUT / 'implementation_options_matrix.csv').open('w', newline='') as f:
    fieldnames = ['option', 'weighted_score_5', 'weighted_score_100', *weights.keys()]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(weighted_rows)

with (OUT / 'implementation_tco_scenarios.csv').open('w', newline='') as f:
    fieldnames = list(costs[0].keys())
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(costs)

plt.rcParams.update({'font.family': 'DejaVu Sans', 'axes.titlesize': 12, 'axes.labelsize': 10})
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), constrained_layout=True)

ordered = sorted(weighted_rows, key=lambda x: x['weighted_score_100'])
axes[0].barh([r['option'] for r in ordered], [r['weighted_score_100'] for r in ordered], color=['#8a6d3b', '#5b8db8', '#2b8c69', '#6c4e8f'])
axes[0].set_xlim(0, 100)
axes[0].set_xlabel('Weighted fit score (0–100)')
axes[0].set_title('Weighted fit for sovereign platform strategy')
for y, r in enumerate(ordered):
    axes[0].text(r['weighted_score_100'] + 1, y, f"{r['weighted_score_100']:.1f}", va='center', fontsize=9)

labels = [r['option'] for r in costs]
x = list(range(len(labels)))
pilot_mid = [((r['pilot_setup_low'] + r['pilot_setup_high']) / 2) / 1000 for r in costs]
prod_mid = [((r['production_setup_low'] + r['production_setup_high']) / 2) / 1000 for r in costs]
width = 0.36
axes[1].bar([i - width / 2 for i in x], pilot_mid, width, label='Pilot one-time midpoint', color='#8bb7d9')
axes[1].bar([i + width / 2 for i in x], prod_mid, width, label='Production one-time midpoint', color='#1f7a5a')
axes[1].set_xticks(x, ['Buy', 'OSS', 'OSS +\nDev', 'Scratch'])
axes[1].set_ylabel('USD thousands (planning midpoint)')
axes[1].set_title('One-time implementation cost bands')
axes[1].legend(frameon=False, fontsize=8)

fig.suptitle('Sovereign AI implementation options — planning analysis', fontsize=14, fontweight='bold')
fig.savefig(OUT / 'implementation_options_comparison.png', dpi=180, bbox_inches='tight')
