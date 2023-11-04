# Exiled Philosophers

This project contains code to automatically generate a dataset of philosophers exiled from Nazi Germany from DBpedia. Furthermore, for each philosopher geo and network data is retrieved from DBpedia and Wikipedia and visualized in a Streamlit dashboard. The dashboard can be accessed at [https://exiled-philosophers.streamlit.app](https://exiled-philosophers.streamlit.app/).

`data` contains the raw and manually processed data sets, as well as an adjacency list for mapping the philosopher network. 

`capta.py` contains the code for generating the data.

`dashboard.py` visualizes the data and prepares it as a streamlit dashboard.

`network_analysis.gephi` is a Gephi project to visualize the same network data and was used to prototype the network visualization in the dashboard.
