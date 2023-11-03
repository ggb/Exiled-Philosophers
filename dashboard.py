import re
import random
from datetime import date
import pandas as pd
import streamlit as st
import numpy as np
import streamlit.components.v1 as components
import networkx as nx
import community.community_louvain as cl 
from streamlit_folium import folium_static
import folium
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pyvis.network import Network

random.seed(13)
np.random.seed(13)

st.set_page_config(page_title="Exiled Philosophers",
                   page_icon=":classical_building:",
                   layout="wide")

@st.cache_data
def get_data():
    df = pd.read_excel("data/philos_manual-adj.xlsx")
    edges = pd.read_excel("data/philos_adj.xlsx")
    df["birthDate"] = pd.to_datetime(df["birthDate"])
    df["deathDate"] = pd.to_datetime(df["deathDate"])
    return df, edges

df, edges = get_data()

pattern = r"_\(.+\)"
def sanitize_name(n):
    n = n.replace("http://de.dbpedia.org/resource/", "")
    return re.sub(pattern, '', n).replace('_', ' ')

df["name"] = df["id"].apply(sanitize_name)
edges = edges.applymap(sanitize_name)

# ----- SIDEBAR ------
# Network related inputs
st.sidebar.header("Network")

net_coloring = st.sidebar.radio("Coloring", 
                                ["Degree Centrality", "Community", "Gender"])

node_size_alg = st.sidebar.radio("Node size",
                                 ["Uniform", "Degree", "SP Betweenness", "Harmonic"],
                                 index=2)

# Map and dataframe related inputs
st.sidebar.header("Map and Raw Data")

include_orphans = st.sidebar.checkbox("Include philosophers without connections", value=True)

map_coloring = st.sidebar.radio("Coloring",
                                ["Born / Died", "Community", "Individual", "Gender"])

born_min, born_max = st.sidebar.slider("Born between",
                                        value=(date(1862, 1, 1), date(1934, 12, 31)))

death_min, death_max = st.sidebar.slider("Died between",
                                          value=(date(1933, 1, 1), date(2023, 12, 31)))


df = df.query(
    "birthDate >= @born_min & birthDate <= @born_max & ((deathDate >= @death_min & deathDate <= @death_max) | missingDeathDate)"
)

###
edges_wo = edges[edges['source'] != edges['target']]
orphaned_philos = set(edges["source"].unique()) - set(edges_wo["source"].unique())

G = nx.from_pandas_edgelist(edges_wo)
partition = cl.best_partition(G)

# Calculate betweenness centrality
betweenness_dict = nx.betweenness_centrality(G)
degrees_dict = nx.degree_centrality(G)
harmonic_dict = nx.harmonic_centrality(G)

def node_size_calc(node):
    if node_size_alg == "Degree":
        return degrees_dict[node]  * 80 + 5
    elif node_size_alg == "SP Betweenness":
        return betweenness_dict[node]  * 80 + 5
    elif node_size_alg == "Harmonic":
        return (harmonic_dict[node] * 0.7) or 3
    else:
        return 5        

def create_born_tooltip(row):
    link = row["id"].replace("http://de.dbpedia.org/resource", "https://de.wikipedia.org/wiki")
    return f"""
<a href="{link}" target="_blank">{row["name"]}</a>, born { row["birthDate"] }.
"""

def create_death_tooltip(row):
    link = row["id"].replace("http://de.dbpedia.org/resource", "https://de.wikipedia.org/wiki")
    return f"""
<a href="{link}" target="_blank">{row["name"]}</a>, died { row["deathDate"] }.
"""

def coord_jitter(coord_str):
    l1, l2 = coord_str.split(" ")
    return (float(l1) + np.random.uniform(0.01, 10**(-20))-0.0005, 
            float(l2) + np.random.uniform(0.01, 10**(-20))-0.0005)

def partition_color(name):
    cmap_cat = cm.get_cmap("tab10") 
    norm = plt.Normalize(min(partition.values()), max(partition.values()))
    if name in partition:
        return mcolors.to_hex(cmap_cat(norm(partition[name])))
    else:
        return "black"

def degree_color(name):
    cmap_con = cm.get_cmap('viridis')
    norm = plt.Normalize(min(degrees_dict.values()), max(degrees_dict.values()))
    return mcolors.to_hex(cmap_con(norm(degrees_dict[name])))

folium_colors = [
    'red',
    'blue',
    'gray',
    'darkred',
    'lightred',
    'orange',
    'beige',
    'green',
    'darkgreen',
    'lightgreen',
    'darkblue',
    'lightblue',
    'purple',
    'darkpurple',
    'pink',
    'cadetblue',
    'lightgray',
    'black'
]
def partition_map_color(name):
    if name in partition:
        return folium_colors[partition[name]]
    else:
        return "black"

def color_marker(row, birth=True):
    if map_coloring == "Born / Died":
        return "blue" if birth else "black"
    elif map_coloring == "Community":
        return partition_map_color(row["name"])
    elif map_coloring == "Gender":
        return "orange" if row["gender"] == "f" else "gray"
    else: 
        return random.choice(folium_colors)

def determine_node_color(node):
    if net_coloring == "Community":
        return partition_map_color(node)
    elif net_coloring == "Gender":
        p = df[df["name"] == node]
        try:
            return "orange" if p["gender"].iloc[0] == "f" else "gray"
        except:
            return "gray"
    else:
        return degree_color(node)


for i, node in enumerate(G.nodes()):
    G.nodes[node]['size'] = node_size_calc(node)
    G.nodes[node]['color'] = determine_node_color(node)


# ----- MAINPAGE -----
st.title(":classical_building: Exiled Philosophers")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Philosophers", len(df))
col2.metric("Communities", max(partition.values()) + 1)
col3.metric("Birth places", len(df["birthPlace"].unique()))
col4.metric("Death places", len(df["deathPlace"].unique()))

st.markdown("""
With the onset of National Socialist rule in Germany in 1933, many German intellectuals, including philosophers, faced increasing exclusion and persecution. While the Law for the Restoration of the Professional Civil Service made academic careers impossible for people of Jewish faith and dissenting political views, hostility also increased, culminating first in the November pogroms, then in the mass murder of the concentration camps. 
            
Those who had the opportunity sooner or later took leave of the German Reich and fled, sometimes under dramatic circumstances. These experiences, the collapse of the democratic Weimar Republic and the seizure of power by a dictator, war, flight and the Shoah, as well as the experience of one's own foreignness in another country with a new language, shaped those who fled and even changed their thinking, but also ensured a strong sense of belonging among themselves. This is true for some of the most influential philosophers of the 20th century, as can be seen in individual biographies and self-testimonies. 
            
This dashboard allows to explore the network of exiled philosophers, as well as to trace the geographical distribution based on places of birth and death. An overview of how the data was obtained and its limitations can be found below the visualizations. 
""")

#
tab1, tab2, tab3 = st.tabs(["Network", "Spatial", "Raw Data"])

with tab1:
    tab1.markdown(f"""
    Zoom in, interact with nodes and explore the network of exiled philosophers! 
    """)
    net = Network()
    net.from_nx(G)
    net.save_graph("tmp.html")
    html_file = open("tmp.html", 'r', encoding='utf-8')
    
    components.html(html_file.read(), height=620)

    tab1.markdown(f"""
    { max(partition.values()) + 1 } communities of philosophers were identified in the network, using the [louvain communities](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html) algorithm.
                  
    The following philosophers had no connections to other philosophers and were removed from the network visualization: { ", ".join(orphaned_philos) }. 
    """)

with tab2:
    m = folium.Map([48.0, 16.0], zoom_start=3)
    without_death_place = []

    for _, row in df.iterrows():
        if not include_orphans and (row["name"] in orphaned_philos):
            continue

        folium.Marker(
                    coord_jitter(row["birthGis"]),
                    popup=create_born_tooltip(row),
                    icon=folium.Icon(color=color_marker(row), icon='cake-candles', prefix='fa')
                    ).add_to(m)
        try:
            folium.Marker(
                        coord_jitter(row["deathGis"]),
                        popup=create_death_tooltip(row),
                        icon=folium.Icon(color=color_marker(row, False), icon='skull', prefix='fa')
                        ).add_to(m)
        except:
            without_death_place.append(row["name"])
    folium_static(m, width=1000)
    tab2.markdown(f"""
        The following philosophers don't have a death place in the data: { ", ".join(without_death_place) }.
        This can have multiple reasons.
    """)

with tab3:
    tab3.dataframe(df)
    #tab3.dataframe(edges_wo)