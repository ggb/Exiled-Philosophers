import pandas as pd
import wikipedia
import spacy
import requests
from SPARQLWrapper import SPARQLWrapper, JSON
from ast import literal_eval

# set wikipedia language to German
wikipedia.set_lang("de")

# German SPARQL DBpedia endpoint
sparql = SPARQLWrapper("http://dbpedia.org/sparql")

def query_philosophers():
    sparql.setQuery("""
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX dbc1: <http://dbpedia.org/resource/Kategorie:Emigrant_aus_dem_Deutschen_Reich_zur_Zeit_des_Nationalsozialismus>
    PREFIX dbc2: <http://dbpedia.org/resource/Kategorie:Philosoph_(20._Jahrhundert)>

    SELECT DISTINCT ?person
    WHERE {
    ?person dcterms:subject dbc1: .
    ?person dcterms:subject dbc2: .
    }
    """)

    sparql.setReturnFormat(JSON)
    return [r['person']['value'] for r in sparql.query().convert()['results']['bindings']]

def query_philosopher_data(unique_name):
    sparql.setQuery(f"""
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX dbr: <http://dbpedia.org/resource/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?name ?birthDate ?deathDate ?birthPlace ?birthGis ?deathPlace ?deathGis
    WHERE {{
    <{ unique_name }> foaf:name ?name .
    OPTIONAL {{<{ unique_name }> dbo:birthDate ?birthDate}}
    OPTIONAL {{<{ unique_name }> dbo:deathDate ?deathDate}}
    OPTIONAL {{<{ unique_name }> dbo:birthPlace ?birthPlaceResource .
                ?birthPlaceResource <http://www.georss.org/georss/point> ?birthGis .
                ?birthPlaceResource rdfs:label ?birthPlace . 
                FILTER (lang(?birthPlace) = 'de')}}
    OPTIONAL {{<{ unique_name }> dbo:deathPlace ?deathPlaceResource .
                ?deathPlaceResource <http://www.georss.org/georss/point> ?deathGis .
                ?deathPlaceResource rdfs:label ?deathPlace . 
                FILTER (lang(?deathPlace) = 'de')}}
    }}
    """)
    sparql.setReturnFormat(JSON)
    vars = ['name', 'birthDate', 'deathDate', 'birthPlace', 'birthGis', 'deathPlace', 'deathGis']
    result =  sparql.query().convert()['results']['bindings']

    extracted_values = {v: set() for v in vars}

    for item in result:
        for var in vars: 
            try:
                extracted_values[var].add(item[var]['value'])
            except KeyError:
                pass
            
    extracted_values['id'] = unique_name

    for v in vars:
        extracted_values[v] = extracted_values[v] - set(["DMS", "DM", "/"])
        if len(extracted_values[v]) == 1 and v != "name":
            extracted_values[v] = list(extracted_values[v])[0]
        elif len(extracted_values[v]) == 0:
            extracted_values[v] = None

    return extracted_values


# As a friendly API consumer I try to reduce API calls: therefore we store intermediate results
philos = pd.DataFrame([query_philosopher_data(p) for p in query_philosophers()])
philos.to_excel("data/philos_raw_new.xlsx", index=False)

#philos = pd.read_excel("data/philos_raw.xlsx")
#philos["name"] = philos["name"].apply(literal_eval)

def check_connection(text, string_set):
    return any(word in text for word in string_set)

def connections_for_philo(philo_id="http://de.dbpedia.org/resource/Heinrich_Walter_Cassirer"):
    page = wikipedia.page(philo_id.replace("http://de.dbpedia.org/resource/", ""), auto_suggest=False)
    philo_con = {}
    for _, row in philos.iterrows():
        philo_con[row["id"]] = check_connection(page.content, row["name"])
    return philo_con

def philos_adjacency():
    adj_list = []
    for _, row in philos.iterrows():
        philosopher = row["id"]
        cons = connections_for_philo(philosopher)
        for key, val in cons.items():
            if val:
                adj_list.append([philosopher, key])

    return adj_list

#adjacencies = pd.DataFrame(philos_adjacency(), columns=["source", "target"])
#adjacencies = adjacencies.applymap(lambda s: s.replace("http://de.dbpedia.org/resource/", ""))
#adjacencies.to_excel("data/philos_adj.xlsx", index=False)

# run: python -m spacy download de_core_news_sm
#nlp = spacy.load('de_core_news_sm')
def perform_ner(philo_id="http://de.dbpedia.org/resource/Hannah_Arendt"):
    page = wikipedia.page(philo_id.replace("http://de.dbpedia.org/resource/", ""), auto_suggest=False)
    doc = nlp(page.content)
    entities = []
    for ent in doc.ents:
        if ent.label_ in ['LOC']:  # Using 'PER' for persons and 'LOC' for locations
            start = max(ent.start - 15, 0)
            end = min(ent.end + 15, len(doc))
            context = doc[start:end]
            entities.append((context.text, ent.text, ent.label_))
    return entities

# This wasn't successful :(
# print(perform_ner())