import json
import pandas as pd
import mysql.connector as connector
import datetime as dt
from mysql.connector import Error
from dotenv import dotenv_values
import os.path
import ast
import pymongo
import locale

# Sert pour la conversion des dates françaises en format datetime
locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')

# Chargement des variables d'environnement
config = dotenv_values('../.env')

def nationality_formatter(nationality : str):
    """
    Fonction de formattage de la nationalité en format anglais

    :param nationality: string contenant la nationalité
    
    :return: Renvoie la version formattée de la nationalité
    """
    dictionnary = { 'Français' : 'France',
                'Française' : 'France',
                'Sénégalaise' : 'Senegal',
                'Portugaise' : 'Portugal',
                'Portugais' : 'Portugal',
                'Marocaine' : 'Morocco',
                'Norvégienne' : 'Norway',
                'Algérienne' : 'Algeria' }
    nat_list = []
    for nat in nationality.split(' '):
        nat_list.append(dictionnary[nat])
    if len(nat_list) > 1 :
        nationality_formatted = ' '.join(nation for nation in nat_list)
    else:
        nationality_formatted = nat_list[0]
    return nationality_formatted

def correct_nationality(string : str):
    """
    Fonction de correction de nationalité
    
    :param string: string contenant la nationalité
    
    :return: string transformée
    """
    if string == "C%C3%B4te d%27Ivoire" :
        return 'Ivory Coast'
    elif string == "the Democratic Republic of the Congo" :
        return 'DR Congo'
    elif string == "the Republic of the Congo":
        return 'Congo'
    else:
        return string

def dataframe_tuple_deserialize(string : str, param : int):
    """
    Fonction de désérialisation des tuples
    
    :param string: string contenant le tuple
    :param param: indice de l'élément du tuple à extraire
    
    :return: l'élément à l'indice *param* du tuple
    """
    tuple_string = ast.literal_eval(string)
    return tuple_string[param]

# Chargement des équipes de Ligue 2 dans un dataframe
df_teams_ligue2 = pd.read_json('../data/teams/ligue2_2022-2024.json', orient='index')
# On reset l'index
df_teams_ligue2.reset_index(inplace=True)
# On renomme la colonne nommée "index" en "name"
df_teams_ligue2.rename(columns={ 'index' : 'name' }, inplace=True)

# Suppresion des artefacts liés au webscraping (les parenthèses et les crochets sur certaines string)
# Voir le notebook pour le détail
df_teams_ligue2['name'] = df_teams_ligue2['name'].str.replace(r' \((.*)\)', "", regex=True)
df_teams_ligue2['stade'] = df_teams_ligue2['stade'].str.replace(r'\[(.*)\]', "", regex=True)

# Chargement des équipes, entraîneurs et joueurs de Ligue 1 depuis les fichiers json
team_names = []
team_shortnames = []
team_founded = []
team_stadium = []
team_coaches = []
team_players = []

# Pour tous les chiffres entre 11 et 77
for i in range(11, 77):
    # On vérifie si le fichier team-5{i}.json existe où i correspond au chiffre entre 11 et 77
    if os.path.isfile(f"../data/teams/team-5{i}.json"):
        # On charge le fichier le cas échéant
        with open(f'../data/teams/team-5{i}.json', 'r') as file:
            data = json.load(file)
            # On vérifie que le fichier n'a pas renvoyé pas une erreur de l'API
            if 'errorCode' not in data:
                # On vérifie que le shortname n'est pas dans la liste suivante 
                # (correspond aux équipes de Ligue 1 qui ont été en Ligue 2 et seront
                # ajoutées avec les données issues du webscraping)
                if data['shortName'] not in ['Le Havre', 'Saint-Étienne', 'Auxerre', 'Angers SCO']:
                    team_names.append(data['name'])
                    team_shortnames.append(data['shortName'])
                    team_founded.append(data['founded'])
                    team_stadium.append(data['venue'])
                    team_coaches.append(data['coach'])
                    team_players.append(data['squad'])

#############################################
# Boucle d'insertion des équipes dans MYSQL #
#############################################
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
        for i in range(len(team_names)):
            add_team_ligue1 = ( "INSERT INTO `Team` (name, shortname, stadium, founded) "
                                f"VALUES (\"{team_names[i]}\", \"{team_shortnames[i]}\", \"{team_stadium[i]}\", {team_founded[i]})" )
            cursor.execute(add_team_ligue1)
        for index, row in df_teams_ligue2.iterrows():
            add_team_ligue2 = ( "INSERT INTO `Team` (name, shortname, stadium, founded) "
                                f"VALUES (\"{row['name']}\", \"{row['shortname']}\", \"{row['stade']}\", {row['fondation']})" )
            cursor.execute(add_team_ligue2)
        cnx.commit()
except Error as e:
    cnx.close()
    print("Erreur lors de la connexion à la base MySQL :", e)
finally:
    if cnx.is_connected():
        cnx.close()
        print('Connexion à la base MySQL fermée')

# Chargement dans un dataframe des données des entraîneurs de Ligue 2 scapés
df_coaches_ligue2 = pd.read_json('../data/teams/coaches_ligue2_2022-2024.json', orient='index')
df_coaches_ligue2.reset_index(inplace=True)
# On supprime les caractères gênants ('\xa0' qui est correspond à un espace et '/')
df_coaches_ligue2['nationality'] = df_coaches_ligue2['nationality'].apply(lambda x: str(x).replace(u'\xa0', u''))
df_coaches_ligue2['nationality'] = df_coaches_ligue2['nationality'].apply(lambda x: str(x).replace(u'/', u' '))
# On utilise la fonction nationality_formatter qui va changer les nationalités en anglais selon un dictionnaire défini dans la fonction
df_coaches_ligue2['nationality'] = df_coaches_ligue2['nationality'].apply(nationality_formatter)
# Suppression des parenthèses dans l'index (nom du club) du dataframe
df_coaches_ligue2['index'] = df_coaches_ligue2['index'].str.replace(r' \((.*)\)', "", regex=True)

# Nettoyage et transformation des dataframe Joueurs issus du webscraping
df_list = []
for team in df_coaches_ligue2['index']:
    df_players_test = pd.read_csv(f'../data/teams/team-{team.replace(' ', '_')}.csv')
    df_players_test = df_players_test[df_players_test.columns[2:6]]
    df_players_test.dropna(inplace=True)
    df_players_test = df_players_test[df_players_test['Nom'] != "('', None)"]
    # Colonne Poste (P.)
    df_players_test[df_players_test.columns[0]] = df_players_test[df_players_test.columns[0]].apply(dataframe_tuple_deserialize, args=(0,))
    dictionnaire_poste = { 'G' : 'Gardien', 'D' : 'Defenseur', 'M' : 'Milieu', 'A' : 'Attaquant'}
    df_players_test[df_players_test.columns[0]] = df_players_test[df_players_test.columns[0]].replace(dictionnaire_poste)
    # Colonne Nationality
    df_players_test[df_players_test.columns[1]] = df_players_test[df_players_test.columns[1]].apply(dataframe_tuple_deserialize, args=(1,))
    df_players_test[df_players_test.columns[1]] = df_players_test[df_players_test.columns[1]].apply(lambda x : x.split('Flag_of_', 1)[1])
    df_players_test[df_players_test.columns[1]] = df_players_test[df_players_test.columns[1]].str.replace(r'_\((.*)\)', "", regex=True)
    df_players_test[df_players_test.columns[1]] = df_players_test[df_players_test.columns[1]].str.replace(".svg", "")
    df_players_test[df_players_test.columns[1]] = df_players_test[df_players_test.columns[1]].str.replace("_", " ")
    df_players_test[df_players_test.columns[1]] = df_players_test[df_players_test.columns[1]].apply(correct_nationality)
    # Colonne Nom
    df_players_test[df_players_test.columns[2]] = df_players_test[df_players_test.columns[2]].apply(dataframe_tuple_deserialize, args=(0,))
    df_players_test[['Prénom', 'Nom']] = df_players_test['Nom'].str.split(' ', n=1, expand=True)
    # Colonne Date de naissance
    df_players_test[df_players_test.columns[3]] = df_players_test[df_players_test.columns[3]].apply(dataframe_tuple_deserialize, args=(0,))
    df_players_test[df_players_test.columns[3]] = df_players_test[df_players_test.columns[3]].str.replace(r'\xa0\((.*)\)', "", regex=True)
    df_players_test[df_players_test.columns[3]] = pd.to_datetime(df_players_test[df_players_test.columns[3]], format="%d/%m/%Y")
    # Colonne equipe
    df_players_test['Equipe'] = team
    df_list.append(df_players_test)

# Extraction de tous les postes issus de l'API
list_position = []
for team in team_players:
    for player in team:
        if player['position'] not in list_position:
            list_position.append(player['position'])

# On utilise le résultat de cette boucle pour créér un dictionnaire de transformation et mettre à jour les postes
for team in team_players:
    for player in team:
        if player['position'] == 'Goalkeeper':
            player['position'] = 'Gardien'
        elif player['position'] in ['Defence', 'Left-Back', 'Right-Back', 'Centre-Back']:
            player['position'] = 'Defenseur'
        elif player['position'] in ['Right Midfield', 'Attacking Midfield', 'Left Midfield', 'Midfield', 'Defensive Midfield', 'Central Midfield']:
            player['position'] = 'Milieu'
        elif player['position'] in ['Right Winger', 'Centre-Forward', 'Left Winger', 'Offence']:
            player['position'] = 'Attaquant'

###############################################################################
# Boucle d'insertion des joueurs et entraîneurs dans la base de données MYSQL #
###############################################################################
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
        team_count = 0
        # Boucle d'ajout pour la Ligue 1 (API)
        for team in team_players:
            # Insertion de l'entraîneur
            cursor.execute("SELECT id FROM `Team` WHERE shortname = %s;", [team_shortnames[team_count]])
            team_id = cursor.fetchone()
            add_coach_ligue1 = ("INSERT INTO `Staff` (first_name, last_name, birthdate, nationality, role, team_id) "
                                f"VALUES (\"{team_coaches[team_count]['name'].split(' ', 1)[0]}\", "
                                f"\"{team_coaches[team_count]['name'].split(' ', 1)[1]}\", \"{team_coaches[team_count]['dateOfBirth']}\", "
                                f"\"{team_coaches[team_count]['nationality']}\", \"Entraineur\", {team_id[0]})" )
            team_count += 1
            cursor.execute(add_coach_ligue1)
            # Boucle d'insertion des joueurs
            for player in team:
                add_player_ligue1 = ("INSERT INTO `Player` (first_name, last_name, birthdate, nationality, position, team_id) "
                                    f"VALUES (\"{player['name'].split(' ', 1)[0]}\", \"{player['name'].split(' ', 1)[1]}\", "
                                    f"\"{player['dateOfBirth']}\", \"{player['nationality']}\", \"{player['position']}\", {team_id[0]})" )
                cursor.execute(add_player_ligue1)
        # Boucle d'ajout pour la Ligue 2 (webscraping)
        for team in df_list:
            # Insertion de l'entraîneur
            cursor.execute("SELECT id FROM `Team` WHERE name = %s;", [team['Equipe'][0]])
            team_id = cursor.fetchone()
            coach = df_coaches_ligue2[df_coaches_ligue2['index'] == team['Equipe'][0]].reset_index()
            add_coach_ligue2 = ("INSERT INTO `Staff` (first_name, last_name, birthdate, nationality, role, team_id) "
                                f"VALUES (\"{coach['surname'][0]}\", \"{coach['name'][0]}\", "
                                f"\"{coach['birthdate'][0]}\", \"{coach['nationality'][0]}\", "
                                f"\"Entraineur\", {team_id[0]})" )
            cursor.execute(add_coach_ligue2)
            # Boucle d'insertion des joueurs
            for index, row in team.iterrows():
                add_player_ligue2 = ("INSERT INTO `Player` (first_name, last_name, birthdate, nationality, position, team_id) "
                                    f"VALUES (\"{row.iloc[4]}\", \"{row.iloc[2]}\", \"{row.iloc[3]}\", \"{row.iloc[1]}\", "
                                    f"\"{row.iloc[0]}\", {team_id[0]})")
                cursor.execute(add_player_ligue2)
        cnx.commit()
except Error as e:
    cnx.close()
    print("Erreur lors de la connexion à la base MySQL :", e)
finally:
    if cnx.is_connected():
        cnx.close()
        print('Connexion à la base MySQL fermée')

# Chargement des classements de Ligue 2 webscrapés dans un dict
df_rankings_list = {}
# Chargement du fichier
with open('../data/competition/ligue2.json', 'r') as file:
    rankings_ligue2 = json.load(file)
    for season in rankings_ligue2:
        for key in rankings_ligue2[season]:
            df = pd.DataFrame(rankings_ligue2[season][key], columns=['position', 'link', 'fullname', 'shortname', 'points', 'played', 'win',
                                                                     'draw', 'loss', 'goalFor', 'goalAgainst', 'goalDiff'])
            df_rankings_list[(int(season), key)] = df.drop(columns=['link', 'goalDiff'])

# Chargement des classements de Ligue 1 obtenus via l'API
df_rankings_list_ligue1 = {}
for season in [2022,2023,2024]:
    with open(f'../data/competition/ligue1_{season}.json', 'r') as file:
        rankings_ligue1 = json.load(file)
        standings_ligue1 = rankings_ligue1['standings']
        df_rankings_list_ligue1[(season, 'HOME')] = pd.DataFrame(standings_ligue1[1]['table']).drop(columns=['form', 'goalDifference'])
        df_rankings_list_ligue1[(season, 'AWAY')] = pd.DataFrame(standings_ligue1[2]['table']).drop(columns=['form', 'goalDifference'])
        df_rankings_list_ligue1[(season, 'TOTAL')] = pd.DataFrame(standings_ligue1[0]['table']).drop(columns=['form', 'goalDifference'])

# On change la colonne team qui contient le nom du club et on utilise le nom abrégé à la place
for key, df in df_rankings_list_ligue1.items():
    df['team'] = df['team'].apply(lambda x : dict(x)['shortName'])

###################################################################
# Boucle d'insertion des classements dans la base de donnée MYSQL #
###################################################################
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
        # Boucle d'ajout des championnats dans MYSQL
        for season in range(2022, 2025):
            for ligue in ['Ligue 1', 'Ligue 2']:
                cursor.execute("INSERT INTO `League` (name, country, season) VALUES (%s,%s,%s)",
                               [ligue, 'France', season])

        # Boucle d'ajout des classements Ligue 1 (API Football-data)        
        for key, df in df_rankings_list_ligue1.items():
            cursor.execute("SELECT id FROM `League` WHERE season = %s AND name = %s;", [key[0], 'Ligue 1'])
            league_id = cursor.fetchone()
            for index, row in df.iterrows():
                cursor.execute("SELECT id FROM `Team` WHERE shortname = %s;", [row['team']])
                team_id = cursor.fetchone()
                if team_id is None:
                    search_similar = f"SELECT id FROM `Team` WHERE shortname LIKE '%{row['team']}%';"
                    cursor.execute(search_similar)
                    team_id = cursor.fetchone()
                add_ranking = ("INSERT INTO `Ranking` (team_id, league_id, type, position, points, played, goals_for, "
                               f"goals_against, won, draw, lost) VALUES ({team_id[0]}, {league_id[0]}, \"{key[1]}\", "
                               f"{row['position']}, {row['points']}, {row['playedGames']}, {row['goalsFor']}, "
                               f"{row['goalsAgainst']}, {row['won']}, {row['draw']}, {row['lost']})")
                cursor.execute(add_ranking)
        # Boucle d'ajout des classements Ligue 2 (webscraping)
        for key, df in df_rankings_list.items():
            cursor.execute("SELECT id FROM `League` WHERE season = %s AND name = %s;", [key[0], 'Ligue 2'])
            league_id = cursor.fetchone()
            for index, row in df.iterrows():
                cursor.execute("SELECT id FROM `Team` WHERE shortname = %s;", [row['shortname']])
                team_id = cursor.fetchone()
                if team_id is None:
                    if row['shortname'] == 'US Quevilly Rouen':
                        cursor.execute("SELECT id FROM `Team` WHERE shortname = %s;", ['US Quevilly-Rouen'])
                        team_id = cursor.fetchone()
                add_ranking = ("INSERT INTO `Ranking` (team_id, league_id, type, position, points, played, goals_for, "
                               f"goals_against, won, draw, lost) VALUES ({team_id[0]}, {league_id[0]}, \"{key[1]}\", "
                               f"{row['position']}, {row['points']}, {row['played']}, {row['goalFor']}, "
                               f"{row['goalAgainst']}, {row['win']}, {row['draw']}, {row['loss']})")
                cursor.execute(add_ranking)
        cnx.commit()
except Error as e:
    cnx.close()
    print("Erreur lors de la connexion à la base MySQL :", e)
finally:
    if cnx.is_connected():
        cnx.close()
        print('Connexion à la base MySQL fermée')

###########
# MONGODB #
###########
client = pymongo.MongoClient('localhost', 27017)
db = client["football_predictor"]
matches_collection = db["matches"]

# Chargement des fichiers json contenant les résultats webscrapés
matches_ligue2 = []
for i in range(2022, 2025):
    with open(f'../data/matches/matches_ligue2_{i}-{i+1}.json') as json_file:
        data = json.load(json_file)
        matches_ligue2.append(data)

# Transformation des dates en français en format 1999-09-09
DATE_FORMAT = "%A %d %B %Y"
for season in matches_ligue2:
    for matchday in season['season_matches']:
        for matches in matchday['matches']:
            matches['date'] = dt.datetime.strptime(matches['date'], DATE_FORMAT).strftime('%Y-%m-%d')

# Transformation des matchs dans une liste à insérer dans MongoDB
matches_mongo = []
for season in matches_ligue2:
    for matchday in season['season_matches']:
        for matches in matchday['matches']:
            matches_mongo.append({'league' : 'Ligue 2',
                                  'season' : season['season'],
                                  'matchday' : matchday['matchday'],
                                  'matches' : matches
                                 })

# Insertion dans la base MongoDB
matches_collection.insert_many(matches_mongo)

# Chargement des fichiers json contenant les résultats de l'API
matches_ligue1 = []
for i in range(2022, 2025):
    matchnumber = 34
    if i == 2022:
        matchnumber = 38
    for j in range(matchnumber):
        with open(f'../data/matches/season-{i}_matches-{j+1}.json') as json_file:
            data = json.load(json_file)
            matches_ligue1.append(data)
# Extraction/Préparation des données pour l'insertion dans MongoDB
matches_mongo = []
for matchday in matches_ligue1:
    matches_temp = []
    for match in matchday['matches']:
        matches_temp.append({ 'date' : match['utcDate'][:10],
                              'home_team' : match['homeTeam']['shortName'],
                              'away_team' : match['awayTeam']['shortName'],
                              'score_halftime' : match['score']['halfTime'],
                              'score' : match['score']['fullTime']})
    matches_mongo.append({ 'league' : matchday['competition']['name'],
                           'season' : f"{matchday['filters']['season']}-{int(matchday['filters']['season']+1)}",
                           'matchday' : int(matchday['filters']['matchday']),
                           'matches' : matches_temp})

# Insertion dans la base MongoDB
matches_collection.insert_many(matches_mongo)

###################################
# Mise à jour des données MongoDB #
###################################

# Récupération des matchs de Ligue 1 dans MongoDB
matchday_cursor = matches_collection.find({"league" : "Ligue 1"})

# Boucle de mise à jour
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
        for matchday in matchday_cursor:
            i = 0
            for match in matchday['matches']:
                search_similar_home = f"SELECT id FROM Team WHERE shortname LIKE '%{match['home_team']}%'"
                cursor.execute(search_similar_home)
                home_team_id = cursor.fetchone()
                search_similar_away = f"SELECT id FROM Team WHERE shortname LIKE '%{match['away_team']}%'"
                cursor.execute(search_similar_away)
                away_team_id = cursor.fetchone()
                team_update = { '$set' : {
                                            f'matches.{i}' : {'date' : match['date'],
                                                              'home_team' : {'id' : int(home_team_id[0]), 'name' : match['home_team']},
                                                              'away_team' : {'id' : int(away_team_id[0]), 'name' : match['away_team']},
                                                              'score_halftime' : match['score_halftime'],
                                                              'score' : match['score']}
                                         }
                              }
                i += 1
                matches_collection.update_one({'_id' : matchday['_id']}, team_update)
    cnx.commit()
except Error as e:
    cnx.close()
    print("Erreur lors de la connexion à la base MySQL :", e)
finally:
    if cnx.is_connected():
        cnx.close()
        print('Connexion à la base MySQL fermée')

# Récupération des matchs de Ligue 2 pour la mise à jour MongoDB
matchday_cursor = matches_collection.find({"league" : "Ligue 2"})

# Boucle de mise à jour
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
        for matchday in matchday_cursor:
            i = 0
            for match in matchday['matches']['results']:
                search_similar_home = f"SELECT id FROM Team WHERE shortname LIKE '%{match['home_team']}%'"
                cursor.execute(search_similar_home)
                home_team_id = cursor.fetchone()
                search_similar_away = f"SELECT id FROM Team WHERE shortname LIKE '%{match['away_team']}%'"
                cursor.execute(search_similar_away)
                away_team_id = cursor.fetchone()
                team_update = { '$set' : {
                                            f'matches.results.{i}' : {
                                                                'home_team' : {'id' : int(home_team_id[0]), 'name' : match['home_team']},
                                                                'score' : match['score'],
                                                                'away_team' : {'id' : int(away_team_id[0]), 'name' : match['away_team']}
                                                        }
                                        }
                            }
                i += 1
                matches_collection.update_one({'_id' : matchday['_id']}, team_update)
    cnx.commit()
except Error as e:
    cnx.close()
    print("Erreur lors de la connexion à la base MySQL :", e)
finally:
    if cnx.is_connected():
        cnx.close()
        print('Connexion à la base MySQL fermée')