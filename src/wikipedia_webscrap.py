import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from io import StringIO
import json
import time

# Liste des adresses contenant les informations liés aux championnats de Ligue 2
# des 3 dernières années que l'on souhaite webscraper
adresse_list = ['https://fr.wikipedia.org/wiki/Championnat_de_France_de_football_de_deuxi%C3%A8me_division_2022-2023',
                'https://fr.wikipedia.org/wiki/Championnat_de_France_de_football_de_deuxi%C3%A8me_division_2023-2024',
                'https://fr.wikipedia.org/wiki/Championnat_de_France_de_football_de_deuxi%C3%A8me_division_2024-2025']


season_dict = {}
##################################################
# Boucle de scraping Classements (BeautifulSoup) #
##################################################
session = requests.session()
for adresse in adresse_list:
    rankings_dict = {}
    response = session.get(adresse)
    soup = BeautifulSoup(response.text, "html.parser")
    # Sélection des tableau contenant les classements (dans l'ordre classement général, classement domicile, classement extérieur)
    ranking_tables = soup.find_all('table', class_='gauche')
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
    # On récupère depuis l'adresse les 4 derniers caractères converti en entier - 1 (l'année de début de saison)
    season_dict[int(adresse[-4:])-1] = rankings_dict
session.close()

############################################################
# Extraction des noms de club depuis le scraping précédent #
############################################################
club_list_address = []
shortname_list = []
longname_list = []
# Pour chaque saison
for season in season_dict:
    # On prend le classement général
    ranking_total = season_dict[season]['TOTAL']
    # Pour chaque entrée du classement
    for ranking in ranking_total:
        # On stocke dans 3 listes distinctes l'ensemble des clubs (leurs noms complets, leurs noms abrégés et leurs liens wiki)
        if ranking[1] not in club_list_address:
            club_list_address.append(ranking[1])
            shortname_list.append(ranking[3])
            longname_list.append(ranking[2])

################################
# Boucle de scraping des Clubs #
################################
session = requests.session()
uri = "https://fr.wikipedia.org"
dict_teams = {}
i = 0
# Pour chaque club dans la liste des liens wiki
for club_address in club_list_address:
    # On charge le contenu de la page et sélectionne la partie infobox (la boîte d'info à droite sur wikipedia)
    response = session.get(uri + club_address)
    soup = BeautifulSoup(response.text, "html.parser")
    infobox = soup.find('div', class_='infobox_v3')
    # Extraction des paramètres Fondation et Stade
    fondation = infobox.find('th', string = re.compile('Fondation')).find_next_sibling('td').get_text()
    stade = infobox.find('a', string = re.compile('Stade')).parent.find_next_sibling('td').get_text()
    # On créé un nouveau dictionnaire pour chaque club utilisant le nom complet comme clé, et ajoute l'année de fondation
    # extraite et le nom du stade traités grâce à des regex
    dict_teams[longname_list[i]] = { 'fondation' : re.search('[0-9]{4}', fondation).group(0), 
                                                        'stade' : re.sub(r' \((.*)\)', '', stade.strip('\n')) }
    i += 1
session.close()

# Ajout du nom abrégé au dictionnaire précédemment créé (les listes étant dans le même ordre)
i = 0
for team in dict_teams:
    dict_teams[team]['shortname'] = shortname_list[i]
    i += 1
dict_teams

#################################################
# Boucles de scraping des Joueurs et Entraîneurs #
#################################################
df_players_list = []
coach_address_list = []
session = requests.session()

# Extraction des joueurs et des entraîneurs
for club_address in club_list_address:
    response = session.get(uri + club_address)
    soup = BeautifulSoup(response.text, "html.parser")
    # Utilisation de la fonction read_html de pandas pour directement convertir le tableau avec Pandas
    df = pd.read_html(StringIO(str(soup.select_one("table.sortable[style='margin:0px; width:100%; text-align: center;']"))), extract_links='body')
    df_players_list.append(df)
    # Extraction de l'entraîneur, le try except sert à gérer les quelques pages qui ont une mise en page différentes des autres
    try:
        coach_address_list.append(soup.find('a', string='Entraîneur').parent.find_next_sibling('td').find('span').find_next_sibling('a').get('href'))
    except AttributeError:
        coach_address_list.append(soup.find('a', string='Entraîneur').parent.find_next_sibling('td').get_text())
session.close()

###################################
# Sauvegarde des données scrapées #
###################################

# Enregistrement dans le fichier ligue2.json des classements
with open(f"../data/competition/ligue2.json", "w") as file:
    file.write(json.dumps(season_dict, indent=4))

# Enregistrement dans le fichier ligue2_2022-2024 des clubs
with open(f"../data/teams/ligue2_2022-2024.json", "w") as file:
    file.write(json.dumps(dict_teams, indent=4))

# Enregistrement dans des fichiers distincts de chaque joueurs par équipe (avec DataFrame.to_csv)
for i in range(len(df_players_list)):
    df_players_list[i][0].to_csv(f"../data/teams/team-{longname_list[i].replace(' ', '_')}.csv")

######################################
# Boucle de scraping des Entraîneurs #
######################################
session = requests.session()
coach_dict = {}
i = 0

# Pour chaque coach dans la liste des coaches précédemment scrapés
for coach in coach_address_list:
    # On vérifie qu'un lien wikipedia a bien été scrapé
    if coach.startswith('/wiki/'):
        uri = "https://fr.wikipedia.org"
        coach_unquote = requests.utils.unquote(uri + coach)
        response = session.get(uri + coach)
        coach_name = re.sub(r' \((.*)\)', '', coach_unquote[30:].replace('_', ' '))
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find(class_='infobox')
        # On extrait la nationalité et la date de naissance
        birthdate = table.find('th', string = re.compile('Naissance')).find_next_sibling('td').find('time').get('datetime')
        nationality = table.find('span', string = re.compile('Nationalité')).parent.find_next_sibling('td').get_text()
    else:
        coach_name = coach.replace('\n ', '')
    # Mise à jour du dictionnaire des entraîneurs avec toutes les informations (Nom/Prénom/Naissance/Nationalité)
    # On effectue des fonctions pour bien supprimer les caractères d'échappement et les espaces en trop, ainsi que split le nom en 2
    coach_dict[longname_list[i]] = { 'surname' : coach_name.split()[0], 'name' : ' '.join(coach_name.split()[1:]),
                                     'birthdate' : birthdate, 'nationality' : nationality.strip('\n').replace('   ','/').strip(' ')}
    i += 1
session.close()

##################################################
# Enregistrement dans un fichier des entraîneurs #
##################################################
with open(f"../data/teams/coaches_ligue2_2022-2024.json", "w") as file:
    file.write(json.dumps(coach_dict, indent=4))

#######################################################################
# Scraping du site média BienPublic.com pour les résultats des matchs #
#######################################################################
session = requests.session()
match_list = []
i = 0

# Pour chaque saison entre 2022-2023 et 2024-2025
for i in range(2022,2025):
    season_dict = {}
    season_dict['season'] = f"{i}-{i+1}"
    # Le nombre de matchs change en fonction de la saison du fait de la réduction du nombre de clubs en 2024
    match_number = 39
    if i == 2024:
        match_number = 35

    # Parcours pour chaque journée de championnat
    for j in range(1,match_number):
        uri = f"https://www.bienpublic.com/sport/calendrier-resultats/saison-{i}-{i+1}/football/national-ligue-2/{j}"
        response = session.get(uri)
        soup = BeautifulSoup(response.text, "html.parser")
        table_list = []
        matchday_dict = {}
        matchday_dict['matchday'] = j

        # On extrait les tables html avec Pandas en DataFrame
        for table in soup.find_all('table'):
            table_list.append(pd.read_html(StringIO(str(table))))
        for table in table_list:
            date_dict = {}
            date_match = table[0].columns[0]
            date_dict['date'] = date_match
            # On renomme les colonnes en équipe domicile / score / équipe extérieur et on transforme en dictionnaire
            date_dict['results'] = table[0].set_axis(['home_team', 'score', 'away_team'], axis='columns').to_dict(orient='records')
            try:
                matchday_dict['matches'].extend([date_dict])
            except KeyError:
                matchday_dict['matches'] = [date_dict]
        # Temps d'attente entre chaque requête pour éviter de trop spammer le site web
        time.sleep(3)
        try:
            season_dict['season_matches'].extend([matchday_dict])
        except KeyError:
            season_dict['season_matches'] = [matchday_dict]
    match_list.append(season_dict)
session.close()

####################################################################
# Enregistrement dans un fichier des résultats/affiches par saison #
####################################################################
for season in match_list:
    with open(f"../data/matches/matches_ligue2_{season['season']}.json", "w") as file:
        file.write(json.dumps(season, indent=4))