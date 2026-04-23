"""
Generate project page figures from v26 dataset.
Outputs PNGs to static/images/ and stats.json.
"""
import csv
import json
import os
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

SRC = r"c:\Users\asmbatati\Desktop\ros_survey_revision\data\ROS2 Related Works_v26.csv"
FW_SRC = r"c:\Users\asmbatati\Desktop\ros_survey_revision\data\ros2pkgs.csv"
OUT = os.path.join(os.path.dirname(__file__), "static", "images")
os.makedirs(OUT, exist_ok=True)

# --- Load data ---
with open(SRC, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

ros1 = [r for r in rows if r.get("ROS Version", "").strip().upper() in ("ROS1", "ROS 1")]
ros2 = [r for r in rows if r.get("ROS Version", "").strip().upper() in ("ROS2", "ROS 2")]
both = [r for r in rows if r.get("ROS Version", "").strip().upper() == "BOTH"]

# Color palette
BLUE = "#2196F3"
GREEN = "#4CAF50"
ORANGE = "#FF9800"
TEAL = "#009688"
PINK = "#E91E63"
PURPLE = "#9C27B0"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# ============================================================
# 1. Publication Growth (stacked bar)
# ============================================================
years = sorted(set(r.get("Year", "").strip() for r in rows if r.get("Year", "").strip().isdigit()))
years = [y for y in years if 2009 <= int(y) <= 2025]

ros1_by_year = Counter(r["Year"].strip() for r in ros1 if r["Year"].strip() in years)
ros2_by_year = Counter(r["Year"].strip() for r in ros2 if r["Year"].strip() in years)
both_by_year = Counter(r["Year"].strip() for r in both if r["Year"].strip() in years)

r1_counts = [ros1_by_year.get(y, 0) for y in years]
r2_counts = [ros2_by_year.get(y, 0) + both_by_year.get(y, 0) for y in years]

fig, ax = plt.subplots(figsize=(12, 5))
x = np.arange(len(years))
ax.bar(x, r1_counts, label="ROS 1", color=BLUE, alpha=0.85)
ax.bar(x, r2_counts, bottom=r1_counts, label="ROS 2", color=GREEN, alpha=0.85)
ax.set_xticks(x)
ax.set_xticklabels(years, rotation=45, ha="right")
ax.set_ylabel("Number of Publications")
ax.set_title("ROS Publication Growth (2009–2025)", fontsize=16, fontweight="bold")
ax.legend()
plt.tight_layout()
fig.savefig(os.path.join(OUT, "publication_growth.png"), dpi=150, bbox_inches="tight")
plt.close()
print("1/7 publication_growth.png")

# ============================================================
# 2. ROS 2 Adoption Rate
# ============================================================
adoption_years = [y for y in years if int(y) >= 2017]
total_by_year = {y: ros1_by_year.get(y, 0) + ros2_by_year.get(y, 0) + both_by_year.get(y, 0) for y in adoption_years}
ros2_pct = [100 * (ros2_by_year.get(y, 0) + both_by_year.get(y, 0)) / max(total_by_year[y], 1) for y in adoption_years]

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(adoption_years, ros2_pct, marker="o", color=GREEN, linewidth=2.5, markersize=8)
ax.fill_between(adoption_years, ros2_pct, alpha=0.15, color=GREEN)
ax.set_ylabel("ROS 2 Share (%)")
ax.set_title("ROS 2 Adoption Rate (% of All Publications)", fontsize=16, fontweight="bold")
ax.yaxis.set_major_formatter(mticker.PercentFormatter())
ax.set_ylim(0, max(ros2_pct) * 1.2)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "ros2_adoption.png"), dpi=150, bbox_inches="tight")
plt.close()
print("2/7 ros2_adoption.png")

# ============================================================
# 3. ROS 2 Research Domains (donut)
# ============================================================
ros2_all = ros2 + both
domain_counts = Counter(r.get("Research_Domain", "").strip() for r in ros2_all if r.get("Research_Domain", "").strip())
labels_d = list(domain_counts.keys())
sizes_d = list(domain_counts.values())
colors_d = [BLUE, GREEN, ORANGE, PINK][:len(labels_d)]

fig, ax = plt.subplots(figsize=(8, 8))
wedges, texts, autotexts = ax.pie(
    sizes_d, labels=labels_d, autopct="%1.1f%%", startangle=90,
    colors=colors_d, pctdistance=0.78, textprops={"fontsize": 11}
)
centre_circle = plt.Circle((0, 0), 0.55, fc="white")
ax.add_artist(centre_circle)
ax.set_title("ROS 2 Research Domains", fontsize=16, fontweight="bold", pad=20)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "ros2_domains.png"), dpi=150, bbox_inches="tight")
plt.close()
print("3/7 ros2_domains.png")

# ============================================================
# 4. Article Type Distribution (pie)
# ============================================================
type_counts = Counter(r.get("Contribution_Type", "").strip() for r in ros2_all if r.get("Contribution_Type", "").strip())
type_labels = {"APP": "Application", "CORE": "Core ROS", "ECO": "Ecosystem"}
labels_t = [type_labels.get(k, k) for k in type_counts.keys()]
sizes_t = list(type_counts.values())
colors_t = [BLUE, ORANGE, TEAL][:len(labels_t)]

fig, ax = plt.subplots(figsize=(7, 7))
ax.pie(sizes_t, labels=labels_t, autopct="%1.1f%%", startangle=90,
       colors=colors_t, textprops={"fontsize": 13})
ax.set_title("ROS 2 Contribution Types", fontsize=16, fontweight="bold", pad=20)
plt.tight_layout()
fig.savefig(os.path.join(OUT, "article_types.png"), dpi=150, bbox_inches="tight")
plt.close()
print("4/7 article_types.png")

# ============================================================
# 5. Top Publishers (horizontal bar)
# ============================================================
pub_counts = Counter(r.get("Publisher", "").strip() for r in ros2_all if r.get("Publisher", "").strip())
top_pubs = pub_counts.most_common(10)
pub_names = [p[0][:40] for p in reversed(top_pubs)]
pub_vals = [p[1] for p in reversed(top_pubs)]

fig, ax = plt.subplots(figsize=(10, 6))
ax.barh(pub_names, pub_vals, color=BLUE, alpha=0.85)
ax.set_xlabel("Number of Publications")
ax.set_title("Top 10 ROS 2 Publishers", fontsize=16, fontweight="bold")
plt.tight_layout()
fig.savefig(os.path.join(OUT, "publishers.png"), dpi=150, bbox_inches="tight")
plt.close()
print("5/7 publishers.png")

# ============================================================
# 6. Package Categories (horizontal bar)
# ============================================================
if os.path.exists(FW_SRC):
    with open(FW_SRC, encoding="utf-8") as f:
        fw_rows = list(csv.DictReader(f))
    
    # Try different column names for category
    cat_col = None
    for candidate in ["robot stack", "infrastructure", "category"]:
        if any(candidate in (r.keys()) for r in fw_rows[:1]):
            cat_col = candidate
            break
    
    if cat_col:
        cat_counts = Counter(r.get(cat_col, "").strip() for r in fw_rows if r.get(cat_col, "").strip())
        top_cats = cat_counts.most_common(15)
        cat_names = [c[0][:35] for c in reversed(top_cats)]
        cat_vals = [c[1] for c in reversed(top_cats)]
        
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.barh(cat_names, cat_vals, color=TEAL, alpha=0.85)
        ax.set_xlabel("Number of Packages")
        ax.set_title(f"ROS 2 Packages by {cat_col.title()}", fontsize=16, fontweight="bold")
        plt.tight_layout()
        fig.savefig(os.path.join(OUT, "pkg_categories.png"), dpi=150, bbox_inches="tight")
        plt.close()
        print("6/7 pkg_categories.png")
    else:
        print("6/7 SKIP: no category column found in frameworks")
else:
    print("6/7 SKIP: frameworks CSV not found")

# ============================================================
# 7. Research Subdomain Distribution (horizontal bar, top 15)
# ============================================================
sub_counts = Counter(r.get("Research_Subdomain", "").strip() for r in ros2_all if r.get("Research_Subdomain", "").strip())
top_subs = sub_counts.most_common(15)
sub_names = [s[0][:40] for s in reversed(top_subs)]
sub_vals = [s[1] for s in reversed(top_subs)]

fig, ax = plt.subplots(figsize=(10, 7))
colors_bar = [BLUE, GREEN, ORANGE, PINK, TEAL, PURPLE] * 3
ax.barh(sub_names, sub_vals, color=colors_bar[:len(sub_names)], alpha=0.85)
ax.set_xlabel("Number of Publications")
ax.set_title("ROS 2 Research Subdomains", fontsize=16, fontweight="bold")
plt.tight_layout()
fig.savefig(os.path.join(OUT, "subdomains.png"), dpi=150, bbox_inches="tight")
plt.close()
print("7/7 subdomains.png")

# ============================================================
# Stats JSON
# ============================================================
stats = {
    "total_papers": len(rows),
    "ros2_papers": len(ros2) + len(both),
    "ros1_papers": len(ros1),
    "years_covered": f"{years[0]}-{years[-1]}",
    "total_packages": len(fw_rows) if os.path.exists(FW_SRC) else 176,
    "domains": len(domain_counts),
}
with open(os.path.join(OUT, "stats.json"), "w") as f:
    json.dump(stats, f, indent=2)
print(f"\nStats: {json.dumps(stats, indent=2)}")
print("Done! All figures regenerated.")
