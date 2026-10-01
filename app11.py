import math
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Patch

st.set_page_config(page_title="Diagnostic AGD", page_icon="⚡", layout="wide")

# ====================== STYLE ======================
plt.rcParams["figure.facecolor"] = "none"   # les graphiques prennent la couleur du fond
plt.rcParams["axes.facecolor"] = "none"

st.markdown(
    """
<style>
/* Fond principal : bleu-gris doux */
.stApp {background: linear-gradient(160deg, #e3ebf5 0%, #cfdbea 100%); color: #1b2733;}
.stApp p, .stApp label, .stApp span, .stApp li, .stApp div {color: #1b2733;}

/* Barre latérale : bleu marine */
[data-testid="stSidebar"] {background: linear-gradient(180deg, #0f2a4a 0%, #1c4a7a 100%);}
[data-testid="stSidebar"] * {color: #f2f6fb !important;}
[data-testid="stSidebar"] input {color: #1b2733 !important; background: #ffffff;}

/* Titres */
h1, h2, h3 {color: #0f2a4a !important;}
h2 {border-bottom: 3px solid #1c5d99; padding-bottom: 6px;}

/* Cartes des indicateurs (rapports) */
[data-testid="stMetric"] {
    background: #f7fafd; border-left: 6px solid #1c5d99; border-radius: 10px;
    padding: 14px 18px; box-shadow: 0 2px 6px rgba(15,42,74,.18);
}
[data-testid="stMetricValue"] {color: #0f2a4a !important; font-weight: 700;}

/* Tableau */
[data-testid="stDataFrame"] {border-radius: 10px; overflow: hidden; box-shadow: 0 2px 6px rgba(15,42,74,.18);}
</style>
""",
    unsafe_allow_html=True,
)

st.title("⚡ Diagnostic des transformateurs par AGD")
st.caption("CEI 60599 : valeurs typiques · rapports de gaz · triangle de Duval · état du papier")

# ====================== SAISIE ======================
erreurs = []


def lire(txt, nom):
    try:
        v = float(txt.replace(",", ".").strip())
        if v < 0:
            raise ValueError
        return v
    except ValueError:
        erreurs.append(nom)
        return 0.0


with st.sidebar:
    st.header("🧪 Saisie des gaz (µl/l)")
    with st.form("saisie"):
        type_t = st.radio("Type de transformateur", ["Sans CPC", "Avec un CPC communicant"])
        st.markdown("**Gaz de défaut**")
        h2 = lire(st.text_input("H₂", "0"), "H₂")
        ch4 = lire(st.text_input("CH₄", "0"), "CH₄")
        c2h4 = lire(st.text_input("C₂H₄", "0"), "C₂H₄")
        c2h6 = lire(st.text_input("C₂H₆", "0"), "C₂H₆")
        c2h2 = lire(st.text_input("C₂H₂", "0"), "C₂H₂")
        st.markdown("**Gaz de l'isolation papier**")
        co = lire(st.text_input("CO", "0"), "CO")
        co2 = lire(st.text_input("CO₂", "0"), "CO₂")
        submit = st.form_submit_button("🔍 Diagnostiquer", type="primary")

if erreurs:
    st.error("Valeur invalide pour : " + ", ".join(erreurs) + ". Entre un nombre positif.")
    st.stop()

# ====================== RÉFÉRENCES ======================
lim_c2h2 = 20 if type_t == "Sans CPC" else 280
gaz_defaut = {"H₂": (h2, 150), "CH₄": (ch4, 130), "C₂H₄": (c2h4, 280),
              "C₂H₆": (c2h6, 90), "C₂H₂": (c2h2, lim_c2h2)}
gaz_papier = {"CO": (co, 600), "CO₂": (co2, 14000)}

ROUGE, VERT = "#d62728", "#2e9e4f"


def ratio(a, b):
    return a / b if b > 0 else float("nan")


def fmt(r):
    return "indéfini" if math.isnan(r) else f"{r:.3f}"


# Tableau 2 : r1 = C2H2/C2H4 ; r2 = CH4/H2 ; r3 = C2H4/C2H6
REGLES = [
    ("DP", "Décharges partielles", lambda r1, r2, r3: r2 < 0.1 and r3 < 0.2),
    ("D1", "Décharges de faible énergie", lambda r1, r2, r3: r1 > 1 and 0.1 <= r2 <= 0.5 and r3 > 1),
    ("D2", "Décharges de forte énergie", lambda r1, r2, r3: 0.6 <= r1 <= 2.5 and 0.1 <= r2 <= 1 and r3 > 2),
    ("T1", "Défaut thermique < 300 °C", lambda r1, r2, r3: r3 < 1),
    ("T2", "Défaut thermique 300–700 °C", lambda r1, r2, r3: r1 < 0.1 and r2 > 1 and 1 <= r3 <= 4),
    ("T3", "Défaut thermique > 700 °C", lambda r1, r2, r3: r1 <= 0.2 and r2 > 1 and r3 > 4),
]

# ====================== TRIANGLE DE DUVAL ======================
# Un point est donné par (b, c) = (%C2H2, %C2H4) ; %CH4 = 100 - b - c
# Sommets : CH4 en haut, C2H2 en bas à gauche, C2H4 en bas à droite
H = math.sqrt(3) / 2


def xy(b, c):
    a = 100 - b - c
    return ((c + a / 2) / 100, a * H / 100)


ZONES = {
    "PD": ([(0, 0), (2, 0), (0, 2)], "#8e44ad", "PD – Décharges partielles"),
    "T1": ([(0, 2), (2, 0), (4, 0), (4, 10), (0, 10)], "#f4d03f", "T1 – Thermique < 300 °C"),
    "T2": ([(0, 10), (4, 10), (4, 50), (0, 50)], "#eb984e", "T2 – Thermique 300–700 °C"),
    "T3": ([(0, 50), (15, 50), (15, 85), (0, 100)], "#cb4335", "T3 – Thermique > 700 °C"),
    "D1": ([(13, 0), (100, 0), (77, 23), (13, 23)], "#85c1e9", "D1 – Décharges faible énergie"),
    "D2": ([(13, 23), (77, 23), (29, 71), (29, 38), (13, 38)], "#2e86c1", "D2 – Décharges forte énergie"),
}
COUL_DT = "#d5d8dc"


def classer_duval(b, c):
    a = 100 - b - c
    if a >= 98:
        return "PD"
    if b >= 13 and c < 23:
        return "D1"
    if b >= 13 and c >= 23 and (c < 38 or b >= 29):
        return "D2"
    if b < 4 and c < 10:
        return "T1"
    if b < 4 and c < 50:
        return "T2"
    if b < 15 and c >= 50:
        return "T3"
    return "DT"


def figure_duval(pb, pc):
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.set_aspect("equal")
    ax.axis("off")

    # fond = zone mixte DT
    fond = [xy(0, 0), xy(100, 0), xy(0, 100)]
    ax.add_patch(Polygon(fond, closed=True, facecolor=COUL_DT, edgecolor="none", zorder=1))
    # zones
    for code, (pts, coul, _) in ZONES.items():
        ax.add_patch(Polygon([xy(*p) for p in pts], closed=True, facecolor=coul,
                             edgecolor="black", linewidth=0.8, zorder=2))
    # grille fine
    for k in range(10, 100, 10):
        for p, q in [((100 - k, 0), (0, 100 - k)),   # CH4 constant
                     ((k, 0), (k, 100 - k)),         # C2H2 constant
                     ((0, k), (100 - k, k))]:        # C2H4 constant
            (x1, y1), (x2, y2) = xy(*p), xy(*q)
            ax.plot([x1, x2], [y1, y2], color="white", lw=0.5, alpha=0.6, zorder=3)
    # contour
    ax.add_patch(Polygon(fond, closed=True, fill=False, edgecolor="black", linewidth=2, zorder=4))

    # graduations
    for k in range(10, 100, 10):
        x, y = xy(100 - k, 0)          # CH4 sur le bord gauche
        ax.text(x - 0.03, y, str(k), ha="right", va="center", fontsize=8)
        x, y = xy(0, k)                # C2H4 sur le bord droit
        ax.text(x + 0.03, y, str(k), ha="left", va="center", fontsize=8)
        x, y = xy(k, 100 - k)          # C2H2 sur la base
        ax.text(x, y - 0.035, str(k), ha="center", va="top", fontsize=8)
    ax.text(0.14, 0.50, "% CH₄", rotation=60, ha="center", va="center", fontsize=11, fontweight="bold")
    ax.text(0.86, 0.50, "% C₂H₄", rotation=-60, ha="center", va="center", fontsize=11, fontweight="bold")
    ax.text(0.5, -0.11, "% C₂H₂", ha="center", va="center", fontsize=11, fontweight="bold")

    # étiquettes des zones fines (flèches vers le bord droit)
    for code, c_cible in [("PD", 1), ("T1", 5), ("T2", 30), ("T3", 75)]:
        ax.annotate(code, xy=xy(0, c_cible), xytext=(48, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=11, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color="black", lw=1))
    # étiquettes des grandes zones
    ax.text(*xy(50, 10), "D1", ha="center", va="center", fontsize=14, fontweight="bold", color="black")
    ax.text(*xy(35, 33), "D2", ha="center", va="center", fontsize=14, fontweight="bold", color="white")
    ax.text(*xy(22, 60), "DT", ha="center", va="center", fontsize=14, fontweight="bold", color="black")

    # échantillon
    x, y = xy(pb, pc)
    ax.scatter([x], [y], marker="*", s=420, c="white", edgecolors="black", linewidths=1.8, zorder=6)
    ax.annotate("Échantillon", xy=(x, y), xytext=(14, 14), textcoords="offset points",
                fontsize=10, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="black"), zorder=7)

    # légende
    handles = [Patch(facecolor=c, edgecolor="black", label=n) for _, (_, c, n) in ZONES.items()]
    handles.append(Patch(facecolor=COUL_DT, edgecolor="black", label="DT – Mixte thermique + électrique"))
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 1.0), fontsize=9, frameon=True)

    ax.set_xlim(-0.12, 1.15)
    ax.set_ylim(-0.17, 0.95)
    fig.tight_layout()
    return fig


# ====================== GRAPHIQUES EN BARRES ======================
def figure_gaz(donnees):
    n = len(donnees)
    fig, axes = plt.subplots(1, n, figsize=(2.3 * n, 3.2))
    if n == 1:
        axes = [axes]
    for ax, (nom, (v, lim)) in zip(axes, donnees.items()):
        coul = ROUGE if v > lim else VERT
        ax.bar([0], [v], color=coul, width=0.6)
        ax.axhline(lim, color="black", linestyle="--", linewidth=1.5)
        haut = max(v, lim) * 1.3 if max(v, lim) > 0 else 1
        ax.set_ylim(0, haut)
        ax.set_xlim(-0.6, 0.6)
        ax.set_xticks([])
        ax.set_title(nom, fontsize=13, fontweight="bold")
        ax.text(0, v, f"{v:g}", ha="center", va="bottom", fontsize=10, fontweight="bold")
        ax.text(0.58, lim, f"limite {lim:g}", ha="right", va="bottom", fontsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    fig.tight_layout()
    return fig


def tableau(donnees):
    lignes = []
    for nom, (v, lim) in donnees.items():
        lignes.append({"Gaz": nom, "Mesure (µl/l)": v, "Valeur typique (µl/l)": lim,
                       "Statut": "🔴 Élevé" if v > lim else "🟢 Normal"})
    return pd.DataFrame(lignes)


# ====================== AFFICHAGE ======================
if not submit:
    st.info("👈 Entre les concentrations dans le panneau de gauche, puis clique sur **Diagnostiquer**.")
    st.stop()

if all(v == 0 for v, _ in list(gaz_defaut.values()) + list(gaz_papier.values())):
    st.warning("Entre au moins une concentration de gaz.")
    st.stop()

depass = [(n, v, l) for n, (v, l) in gaz_defaut.items() if v > l]
r1, r2, r3 = ratio(c2h2, c2h4), ratio(ch4, h2), ratio(c2h4, c2h6)
trouves = [(c, n) for c, n, f in REGLES if f(r1, r2, r3)] if depass else []

# ---------- Résumé ----------
st.header("Résultat")
if not depass:
    st.success("✅ **Aucun défaut détecté** : H₂, CH₄, C₂H₄, C₂H₆ et C₂H₂ sont dans les valeurs typiques.")
elif trouves:
    st.error("🔴 **Défaut probable : " + " / ".join(f"{c} ({n})" for c, n in trouves) + "**")
else:
    st.warning("⚠️ Gaz anormaux détectés mais aucun cas exact du tableau : défaut possiblement mixte.")

# ---------- 1. Gaz ----------
st.header("1. Gaz mesurés et valeurs typiques")
st.caption("Barre rouge = au-dessus de la valeur typique · barre verte = normal · tireté noir = limite")
c_tab, c_graph = st.columns([1, 2])
c_tab.dataframe(tableau(gaz_defaut), hide_index=True)
c_graph.pyplot(figure_gaz(gaz_defaut))

# ---------- 2. Rapports ----------
st.header("2. Méthode des rapports (Tableau 2)")
if not depass:
    st.info("Les rapports ne sont calculés que si au moins un gaz dépasse la valeur typique (Note 2).")
else:
    m1, m2, m3 = st.columns(3)
    m1.metric("C₂H₂ / C₂H₄", fmt(r1))
    m2.metric("CH₄ / H₂", fmt(r2))
    m3.metric("C₂H₄ / C₂H₆", fmt(r3))
    if len(trouves) > 1:
        st.warning("Plusieurs cas correspondent : confirme avec le triangle de Duval.")
    elif not trouves:
        st.warning("Aucun cas exact : utilise le triangle de Duval ci-dessous.")

# ---------- 3. Duval ----------
st.header("3. Triangle de Duval")
total = ch4 + c2h4 + c2h2
if total == 0:
    st.info("CH₄, C₂H₄ et C₂H₂ sont nuls : le triangle de Duval n'est pas applicable.")
else:
    pb, pc, pa = 100 * c2h2 / total, 100 * c2h4 / total, 100 * ch4 / total
    zone = classer_duval(pb, pc)
    nom_zone = "Mixte thermique + électrique" if zone == "DT" else ZONES[zone][2]
    if not depass:
        st.info("Les gaz sont dans les valeurs typiques : le point est affiché à titre indicatif, "
                "il n'est pas significatif (Note 2).")
    d1, d2 = st.columns([2, 1])
    d1.pyplot(figure_duval(pb, pc))
    with d2:
        st.subheader("Zone : " + zone)
        st.write(nom_zone)
        st.metric("% CH₄", f"{pa:.1f} %")
        st.metric("% C₂H₄", f"{pc:.1f} %")
        st.metric("% C₂H₂", f"{pb:.1f} %")
        if depass and trouves:
            if any(zone == c for c, _ in trouves):
                st.success("Les deux méthodes concordent.")
            else:
                st.warning("Les deux méthodes diffèrent : refais une analyse pour suivre l'évolution.")

# ---------- 4. Papier ----------
st.header("4. Isolation papier (CO₂ / CO)")
st.caption("CO et CO₂ n'interviennent pas dans le type de défaut : ils indiquent seulement l'état du papier.")
p1, p2 = st.columns([1, 1])
p1.pyplot(figure_gaz(gaz_papier))
with p2:
    if co > 0 and co2 > 0:
        rp = co2 / co
        st.metric("CO₂ / CO", f"{rp:.2f}", "seuil de la norme : 3", delta_color="off")
        co_haut, co2_haut = co > 600, co2 > 14000
        if rp < 3:
            st.error("🟠 CO₂/CO < 3 : papier probablement impliqué (carbonisation possible). "
                     "Demander une analyse des composés furaniques ou du degré de polymérisation.")
        elif co_haut or co2_haut:
            st.warning("🟡 CO ou CO₂ élevé mais CO₂/CO ≥ 3 : pas de défaut papier. Cause probable : "
                       "vieillissement normal, air dissous ou oxydation de l'huile. Surveiller l'évolution.")
        else:
            st.success("✅ Papier normal : CO et CO₂ typiques, CO₂/CO ≥ 3.")
        st.caption("Rigoureusement, CO et CO₂ doivent être corrigés de l'air atmosphérique "
                   "(jusqu'à ~300 µl/l de CO₂) et des valeurs accumulées (article 5.4).")
    else:
        st.info("Entre CO et CO₂ (non nuls) pour évaluer l'état du papier.")