import os
import jwt
import datetime
from fastapi import FastAPI, Query, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import mysql.connector
from typing import Optional
from pydantic import BaseModel
from dotenv import dotenv_values

config = dotenv_values()

app = FastAPI()

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

@app.get("/equipe")
async def get_employees(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    name: Optional[str] = Query(None, alias="name"),
    id: Optional[int] = Query(None, alias="id"),
    limit: Optional[int] = Query(10, alias="limit")
):
    """
    Route qui permet de récupérer les équipes en fonction de différents critères
    
    :param credentials: Credentials pour l'authentification

    :param name: Nom approximatif de l'équipe recherchée

    :param id: Identifiant unique de l'équipe

    :param limit: Nombre d'équipes limite à retourner

    :return: Liste des employés
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
async def get_player(
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
    
    :param credentials: Token d'authentification

    :param id: Identifiant du joueur

    :param prenom: Prénom du joueur

    :param nom: Nom de famille du joueur

    :param naissance: Date de naissance du joueur (format : YYYY-MM-dd)

    :param position: Position dans l'équipe (valeur possibles : 'Gardien', 'Defenseur', 'Milieu', 'Attaquant')

    :param team: Nom de l'équipe

    :param limit: Nombre maximum de joueurs affichés (30 par défaut)

    :return: Liste des joueurs correspondant aux critères
    """
    await verify_token(credentials)

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    query = ""
    if team:
        query = f"SELECT Player.* FROM Player JOIN Team ON Player.team_id = Team.id WHERE name LIKE '%{team}%'"
    else:
        query = "SELECT * FROM Player WHERE 1=1"
    params = []

    if id:
        query += " AND id = %s"
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)