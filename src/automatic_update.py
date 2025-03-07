import mysql.connector as connector
from mysql.connector import Error
import pymongo
from dotenv import dotenv_values
import datetime as dt
from bs4 import BeautifulSoup
import requests
import json
import pandas as pd

# Chargement des variables d'environnement pour les connexions BDD
config = dotenv_values("../.env")

# La page du championnat de Ligue 2 actuel
URIwebscrap = "https://fr.wikipedia.org/wiki/Championnat_de_France_de_football_de_deuxi%C3%A8me_division_2024-2025"
# La requête de l'API pour le classement du championnat de Ligue 1 actuel
URIfootballdata = "https://api.football-data.org/v4/competitions/FL1/standings?season=2024"

# API Football-data Ligue 1
session = requests.session()
session.headers.update({ 'X-Auth-Token' : config['FOOTBALL_DATA_API_KEY'] })
response = session.get(URIfootballdata)
parsed_response = json.loads(response.text)
session.close()

# Stockage dans un dictionnaire contenant 3 dataframes pour chaque type de classement
df_rankings_update = {}
standings_ligue1 = parsed_response['standings']
df_rankings_update['HOME'] = pd.DataFrame(standings_ligue1[1]['table']).drop(columns=['form', 'goalDifference'])
df_rankings_update['AWAY'] = pd.DataFrame(standings_ligue1[2]['table']).drop(columns=['form', 'goalDifference'])
df_rankings_update['TOTAL'] = pd.DataFrame(standings_ligue1[0]['table']).drop(columns=['form', 'goalDifference'])

# Webscraping Ligue 2
session = requests.session()
response = session.get(URIwebscrap)
soup = BeautifulSoup(response.text, "html.parser")
ranking_tables = soup.find_all('table', class_='gauche')
session.close()

# Transformation en dictionnaire par type contenant l'ensemble des statistiques de classement sous forme de liste
rankings_dict = {}
i = 0
for table in ranking_tables:
    rankings = table.find_all('tr', class_='notheme')
    rankings_list = []
    # Parcours de chaque ligne et extraction du nom du club, du nom abrévié, du lien wikipedia du club, et des statistiques
    for line in rankings:
        ranking_entry = []
        for td in line.find_all('td'):
            if td.find('a'):
                ranking_entry.append(td.find('a').get('href'))
                ranking_entry.append(td.find('a').get('title'))
                ranking_entry.append(td.find('a').get_text().strip('\n'))
            elif td.find('span'):
                ranking_entry.append(td.find('b').get_text().strip('\n'))
            else:
                ranking_entry.append(td.get_text().strip('\n'))
        rankings_list.append(ranking_entry)
    # Ajout du type de classement correspondant (TOTAL = classement général, HOME = domicile, AWAY = extérieur)
    if i == 0:
        rankings_dict['TOTAL'] = rankings_list
    elif i == 1:
        rankings_dict['HOME'] = rankings_list
    else:
        rankings_dict['AWAY'] = rankings_list
    i += 1

# Transformation des listes de statistiques en un DataFrame
df_rankings_list = {}
for key in rankings_dict:
    df = pd.DataFrame(rankings_dict[key], columns=['position', 'link', 'fullname', 'shortname', 'points', 'played', 'win',
                                                                'draw', 'loss', 'goalFor', 'goalAgainst', 'goalDiff'])
    df_rankings_list[key] = df.drop(columns=['link', 'goalDiff'])
##########################################
# Script de MAJ des classements sur MySQL#
##########################################
try:
    cnx = connector.connect(host='localhost',
                            database='football_predictor',
                            user=config['MYSQL_USER'],
                            password=config['MYSQL_PASSWORD'],
                            )
    if cnx.is_connected():
        print('Connecté à la base MySQL')
        cursor = cnx.cursor()
        # Chargement des données dans la base données SQL            
        for key, df in df_rankings_update.items():
            cursor.execute("SELECT id FROM `League` WHERE season = 2024 AND name = 'Ligue 1';")
            league_id = cursor.fetchone()
            for index, row in df.iterrows():
                cursor.execute("SELECT id FROM `Team` WHERE shortname = %s;", [row['team']['shortName']])
                team_id = cursor.fetchone()
                if team_id is None:
                    search_similar = f"SELECT id FROM `Team` WHERE shortname LIKE '%{row['team']['shortName']}%';"
                    cursor.execute(search_similar)
                    team_id = cursor.fetchone()
                update_ranking = ("UPDATE `Ranking` SET position = %s, points = %s, played = %s, goals_for = %s, "
                                  "goals_against = %s, won = %s, draw = %s, lost = %s "
                                  "WHERE team_id = %s AND league_id = %s AND type = %s;")
                params = [row["position"], row["points"], 
                          row["playedGames"], row["goalsFor"], 
                          row["goalsAgainst"], row["won"], 
                          row["draw"], row["lost"], team_id[0], league_id[0],
                          key]
                cursor.execute(update_ranking, params=params)
        for key, df in df_rankings_list.items():
            cursor.execute("SELECT id FROM `League` WHERE season = 2024 AND name = 'Ligue 2';")
            league_id = cursor.fetchone()
            for index, row in df.iterrows():
                cursor.execute("SELECT id FROM `Team` WHERE shortname = %s;", [row['shortname']])
                team_id = cursor.fetchone()
                if team_id is None:
                    search_similar = f"SELECT id FROM `Team` WHERE shortname LIKE '%{row['shortName']}%';"
                    cursor.execute(search_similar)
                    team_id = cursor.fetchone()
                update_ranking = ("UPDATE `Ranking` SET position = %s, points = %s, played = %s, goals_for = %s, "
                                  "goals_against = %s, won = %s, draw = %s, lost = %s "
                                  "WHERE team_id = %s AND league_id = %s AND type = %s;")
                params = [int(row["position"]), int(row["points"]), 
                          int(row["played"]), int(row["goalFor"]), 
                          int(row["goalAgainst"]), int(row["win"]), 
                          int(row["draw"]), int(row["loss"]), team_id[0], league_id[0],
                          key]
                cursor.execute(update_ranking, params=params)
        cnx.commit()
except Error as e:
    cnx.close()
    print("Erreur lors de la connexion à la base MySQL :", e)
finally:
    if cnx.is_connected():
        cnx.close()
        print('Connexion à la base MySQL fermée')

