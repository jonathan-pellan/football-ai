import requests
import json
import time
import os
from dotenv import dotenv_values

# URI correspondant à la Ligue 1 sur l'API Football-data
uri = "https://api.football-data.org/v4/competitions/FL1/"

# Chargement des données d'environnement
config = dotenv_values('../.env')

session = requests.session()
# Token API secret pour la requête
session.headers.update({ 'X-Auth-Token' : config['FOOTBALL_DATA_API_KEY'] })
for i in range(2022, 2025):
    # Requête à l'API
    uri_competition = uri + "standings?season=" + str(i)
    response = session.get(uri_competition)
    parsed_response = json.loads(response.text)
    # Enregistrement du résultat dans un fichier
    with open(f"../data/ligue1_{i}.json", "w") as file:
        file.write(json.dumps(parsed_response, indent=4))
    # Temps d'attente entre requêtes
    time.sleep(90)
session.close()

# Extraction des ids des équipes de cette saison et stockage dans une liste
# L'API nous limitant aux équipes actuellement en Ligue 1
# On utilisera le webscraping pour compenser les manques (équipes qui sont descendus en Ligue 2 ou National)
team_id_list = []
json_path = '../data/competition/ligue1_2024.json'
if os.path.isfile(json_path):
    with open(json_path, "r") as json_data:
        data = json.load(json_data)
        for element in data['standings'][0]['table']:
            if element['team']['id'] not in team_id_list:
                team_id_list.append(element['team']['id'])
        json_data.close()

#####################################################################
# Boucle de récupération des équipes (club, joueurs et entraîneurs) #
#####################################################################

# Endpoint de l'API pour les équipes
uri = "https://api.football-data.org/v4/teams/"
session = requests.session()
# Token API secret pour la requête
session.headers.update({ 'X-Auth-Token' : config['FOOTBALL_DATA_API_KEY'] })
# Pour chaque id d'équipe dans la liste
for id in team_id_list:
    with open("../data/teams/team-"+ str(id) +".json", "w") as file:
        uri_competition = uri + str(id)
        # On requête l'API sur cet id
        response = session.get(uri_competition)
        parsed_response = json.loads(response.text)
        # On créé un fichier pour chaque équipe
        file.write(json.dumps(parsed_response, indent=4))
        # Temps d'attente entre 2 requêtes
        time.sleep(90)
session.close()

#############################################################################
# Boucle de récupération des résultats pour chaque journée de chaque saison #
#############################################################################

session = requests.session()
session.headers.update({ 'X-Auth-Token' : config['FOOTBALL_DATA_API_KEY'] })

# Pour chaque saison entre 2022 et 2024
for i in range(2022,2025):
    # Pour la saison 2022
    if i == 2022:
        # Pour chaque journée (38)
        for j in range(38):
            # Requête de l'API
            response = session.get(f"https://api.football-data.org/v4/competitions/FL1/matches?season={i}&matchday={j+1}")
            # Enregistrement dans un fichier
            with open(f"../data/matches/season-{i}_matches-{j+1}.json", "w") as file:
                parsed_response = json.loads(response.text)
                file.write(json.dumps(parsed_response, indent=4))
            # Attente entre 2 requêtes
            time.sleep(90)
    # Pour les autres saisons
    else:
        # Pour chaque journée (34)
        for j in range(35):
            # Requête de l'API
            response = session.get(f"https://api.football-data.org/v4/competitions/FL1/matches?season={i}&matchday={j+1}")
            # Enregistrement dans un fichier
            with open(f"../data/matches/season-{i}_matches-{j+1}.json", "w") as file:
                parsed_response = json.loads(response.text)
                file.write(json.dumps(parsed_response, indent=4))
            # Attente entre 2 requêtes
            time.sleep(90)
session.close()