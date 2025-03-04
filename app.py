import jwt
import datetime
from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import mysql.connector
import pymongo
from typing import Optional
from pydantic import BaseModel
from dotenv import dotenv_values

config = dotenv_values()

description = """
FootballPredictorApp API permet d'accéder à des données sur les championnats de football français. 🚀

## Équipe

On peut **lire** les équipes existantes.

## Joueurs

Il est possible de :

* ** Lire les entrées de joueurs de la bdd.

## Classements

Il est possible de :

* Lire les entrées de classements selon les paramètres précisés
"""

app = FastAPI(title="FootballPredictorApp",
              description=description,
              summary="API pour accéder à la base de données des résultats des championnats français",
              version="0.0.2",
              contact={
                "name": "Jonathan Pellan",
                "email": "jonathan.pellan@protonmail.com",
              })

# Configuration de la sécurité
security = HTTPBearer()

# Modèle pour l'authentification
class TokenRequest(BaseModel):
    password: str
    duration: Optional[int] = 3600  # Durée en secondes (1h par défaut)

def create_jwt(duration: int) -> str:
    """
    Fonction qui permet de générer un token JWT
    
    :param duration: Durée de validité du token en secondes
    :return: Token JWT encodé
    """
    expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=duration)
    return jwt.encode(
        {"exp": expiration},
        config['SECRET_KEY'],
        algorithm="HS256"
    )

@app.post("/token")
def generate_token(request: TokenRequest):
    """
    Route qui permet de générer un token pour un utilisateur qui saisit son mot de passe
    
    :param request: Objet TokenRequest contenant le mot de passe et la durée
    :return: Token JWT
    """
    if request.password != config['API_PASSWORD']:
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_jwt(request.duration)
    return {"token": token}

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Fonction qui permet de vérifier le token JWT
    
    :param credentials: Credentials fournis via le bearer token
    :return: None
    :raises: HTTPException si le token est invalide ou expiré
    """
    try:
        jwt.decode(credentials.credentials, config['SECRET_KEY'], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_db_connection():
    """
    Fonction qui permet de se connecter à la base de données MySQL
    
    :return: Objet connexion à la base de données
    """
    return mysql.connector.connect(
        host=config['MYSQL_HOST'],
        user=config['MYSQL_USER'],
        password=config['MYSQL_PASSWORD'],
        database="football_predictor"
    )

def get_mongodb_connection():
    """
    Fonction qui permet de se connecter à la base de données MongoDB locale

    :return: Objet MongoClient
    """
    client = pymongo.MongoClient('localhost', 27017)
    return client

@app.get("/equipe")
async def get_team(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    name: Optional[str] = Query(None, alias="name"),
    id: Optional[int] = Query(None, alias="id"),
    limit: Optional[int] = Query(10, alias="limit")
):
    """
    Route qui permet de récupérer les équipes en fonction de différents critères
    
    - **credentials**: Credentials pour l'authentification
    - **name**: Nom approximatif de l'équipe recherchée
    - **id**: Identifiant unique de l'équipe
    - **limit**: Nombre d'équipes limite à retourner

    *Renvoie la liste des équipes correspondant aux critères*
    """
    # Vérification du token
    await verify_token(credentials)
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    query = "SELECT * FROM Team WHERE 1=1"
    params = []

    if name:
        query += f" AND name LIKE '%{name}%'"
        #params.append(name)
    if id:
        query += " AND id = %s"
        params.append(id)

    query += " LIMIT %s"
    params.append(limit)

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    connection.close()

    return results

@app.get("/joueurs")
async def get_players(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        id : Optional[int] = Query(None, alias='id'),
        first_name : Optional[str] = Query(None, alias='prenom'),
        last_name : Optional[str] = Query(None, alias='nom'),
        birth_date : Optional[str] = Query(None, alias='naissance'),
        position : Optional[str] = Query(None, alias='position'),
        team : Optional[str] = Query(None, alias='equipe'),
        limit : Optional[int] = Query(30, alias='limit')
):
    """
    Route permettant de récupérer les joueurs en fonction de différents critères
    
    - **credentials**: Token d'authentification
    - **id**: Identifiant du joueur
    - **prenom**: Prénom du joueur
    - **nom**: Nom de famille du joueur
    - **naissance**: Date de naissance du joueur (format : YYYY-MM-dd)
    - **position**: Position dans l'équipe (valeurs possibles : 'Gardien', 'Defenseur', 'Milieu', 'Attaquant')
    - **team**: Nom de l'équipe
    - **limit**: Nombre maximum de joueurs affichés (30 par défaut)

    *Renvoie la liste des joueurs correspondant aux critères*
    """
    await verify_token(credentials)

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    query = ""
    if team:
        query = f"SELECT Player.* FROM Player JOIN Team ON Player.team_id = Team.id WHERE (name LIKE '%{team}%' OR shortname LIKE '%{team}%')"
    else:
        query = "SELECT * FROM Player WHERE 1=1"
    params = []

    if id:
        query += " AND Player.id = %s"
        params.append(id)
    if first_name:
        query += " AND first_name = %s"
        params.append(first_name)
    if last_name:
        query += " AND last_name = %s"
        params.append(last_name)
    if birth_date:
        query += " AND birthdate = %s"
        params.append(birth_date)
    if position and position in ['Gardien', 'Defenseur', 'Milieu', 'Attaquant']:
        query += " AND position = %s"
        params.append(position)
    
    query += " LIMIT %s"
    params.append(limit)

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    connection.close()
    return results

@app.get('/classements')
async def get_rankings(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        season: Optional[int] = Query(None, alias='saison'),
        type_: Optional[str] = Query(None, alias='type'),
        team: Optional[str] = Query(None, alias='equipe'),
        league: Optional[str] = Query(None, alias='championnat'),
        limit: Optional[int] = Query(10, alias='limit')
):
    """
    Route permettant d'accéder aux historiques de classement

    - **credentials**: Token d'authentification
    - **season**: Année de début de la saison (ex : pour 2022-2023, on utilise 2022)
    - **type_**: Type de classement ('TOTAL', 'HOME', 'AWAY')
    - **team**: Nom de l'équipe
    - **league**: Compétition à sélectionner
    - **limit**: Nombre maximum de résultats (10 par défaut)

    *Renvoie la liste des classements correspondant à la requête*
    """
    await verify_token(credentials)

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    query = ("SELECT position, league.name, league.season, team.name, type, played, goals_for, "
             "goals_against, won, draw, lost, points FROM `Ranking` JOIN `Team` ON Ranking.team_id = Team.id"
             " JOIN `League` ON Ranking.team_id = League.id WHERE 1=1")
    params = []

    if season:
        query += " AND League.season = %s"
        params.append(season)
    if team:
        query += " AND (Team.name LIKE '%%%s%' OR Team.shortname LIKE '%%%s%')"
        params.append(team)
        params.append(team)
    if league:
        query += " AND League.name = %s"
        params.append(league)
    if type_:
        query += " AND type = %s"
        params.append(type_)

    query += " LIMIT %s"
    params.append(limit)

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    connection.close()
    return results

@app.get('/matches')
async def get_matches(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        season: Optional[int] = Query(None, alias='saison'),
        matchday: Optional[int] = Query(None, alias='journee'),
        league: Optional[str] = Query(None, alias='championnat'),
        limit: Optional[int] = Query(10, alias='limit')
):
    """
    Route permettant d'accéder aux résultats/affiches des matchs
    
    - **credentials** : Token d'authentification
    - **season** : Année de début de la saison
    - **matchday** : Journée à sélectionner (entre 1 et 34 ou 38 selon la saison)
    - **league** : Championnat à sélectionner ('Ligue 1' et 'Ligue 2')
    
    *Renvoie la liste des résultats/affiches correspondant à la requête"""
    await verify_token(credentials)

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    client = get_mongodb_connection()
    db = client['football_predictor']
    matches = db['matches']
    query = {}

    if season:
        query['season'] = str(f"{season}-{season+1}")
    if matchday:
        query['matchday'] = matchday
    if league and league in ['Ligue 1', 'Ligue 2']:
        query['league'] = league

    results_mongo = matches.find(query, projection={ '_id' : False }, limit=limit)
    results = list(results_mongo)
    client.close()
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)