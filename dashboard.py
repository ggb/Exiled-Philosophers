import re
import random
import pandas as pd
import streamlit as st
import numpy as np
import streamlit.components.v1 as components
import networkx as nx
import community
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
    #df["birthDate"] = pd.to_datetime(df["birthDate"], format="%Y")
    #df["deathDate"] = pd.to_datetime(df["deathDate"], format="%Y")
    return df, edges

df, edges = get_data()

pattern = r"_\(.+\)"
def sanitize_name(n):
    n = n.replace("http://de.dbpedia.org/resource/", "")
    return re.sub(pattern, '', n).replace('_', ' ')

df["name"] = df["id"].apply(sanitize_name)
edges = edges.applymap(sanitize_name)

# ----- SIDEBAR ------
st.sidebar.header("Network")

net_coloring = st.sidebar.radio("Coloring", 
                                ["Grade", "Community"])

st.sidebar.header("Map and Raw Data")

map_coloring = st.sidebar.radio("Coloring",
                                ["Born / Died", "Community", "Individual"])

# ----- MAINPAGE -----
st.title(":classical_building: Exiled Philosophers")
st.markdown("""
##
           
""")


###
edges_wo = edges[edges['source'] != edges['target']]
orphaned_philos = set(edges["source"].unique()) - set(edges_wo["source"].unique())

G = nx.from_pandas_edgelist(edges_wo)
partition = community.best_partition(G)

# Calculate betweenness centrality
betweenness_dict = nx.betweenness_centrality(G)
degrees_dict = nx.degree_centrality(G)

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
        print(mcolors.to_hex(cmap_cat(norm(partition[name]))))
        return mcolors.to_hex(cmap_cat(norm(partition[name])))
    else:
        return "black"

def degree_color(name):
    cmap_con = cm.get_cmap('viridis')
    norm = plt.Normalize(min(degrees_dict.values()), max(degrees_dict.values()))
    return mcolors.to_hex(cmap_con(norm(degrees_dict[name])))

def partition_map_color(name):
    colors = [
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
    if name in partition:
        return colors[partition[name]]
    else:
        return "black"


for i, node in enumerate(G.nodes()):
    G.nodes[node]['size'] = betweenness_dict[node] * 80 + 5
    G.nodes[node]['color'] = partition_map_color(node) if net_coloring == "Community" else degree_color(node)


#
tab1, tab2, tab3 = st.tabs(["Network", "Spatial", "Raw Data"])


with tab1:
    net = Network()
    net.from_nx(G)
    net.save_graph("tmp.html")
    html_file = open("tmp.html", 'r', encoding='utf-8')
    
    components.html(html_file.read(), height=620)

    tab1.markdown(f"""
    The following philosophers had no connections to other philosophers and were removed from the network visualization: { ", ".join(orphaned_philos) }. 
    """)

with tab2:
    m = folium.Map([48.0, 16.0], zoom_start=3)
    without_death_place = []

    for _, row in df.iterrows():
        folium.Marker(
                    coord_jitter(row["birthGis"]),
                    popup=create_born_tooltip(row),
                    icon=folium.Icon(color=partition_map_color(row["name"]), icon='cake-candles', prefix='fa')
                    ).add_to(m)
        try:
            folium.Marker(
                        coord_jitter(row["deathGis"]),
                        popup=create_death_tooltip(row),
                        icon=folium.Icon(color=partition_map_color(row["name"]), icon='skull', prefix='fa')
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
    tab3.dataframe(edges_wo)