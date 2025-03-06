# football-ai
L'application football-ai est une application permettant à partir de données historiques et actualisées régulièrement de championnats de football, de faire des prédictions de résultats. L'application ne supporte actuellement que les championnats français de Ligue 1 et Ligue 2, mais sera étendue à l'avenir à d'autres championnats.

## Changelog
* 0.1.1
    - Mise à jour de la documentation
    - Ajout d'un template pour le fichier *.env* : **.env.example**
    - Ajout de la structure de dossier pour stocker les fichiers issus du webscraping et des requêtes *football-data*
    - Ajout de l'équipe inconnue dans le script de création de la BDD MySQL
    - Modification de la docstring de l'API

* 0.1.0
    - scripts d'importation des données depuis différentes sources (**src/football_data_api.py** & **src/wikipedia_webscrap.py**)
    - script de création de la base de donnée MySQL (**src/football_bdd.sql**)
    - script de nettoyage, d'agrégation et d'insertion des données (**src/data_cleaning_insertion.py**)
    - API (**app.py**)


## Installation
Le fichier **requirements.txt** contient l'ensemble des librairies nécessaires à l'éxécution du code de ce projet. Une fois un environnement virtuel Python créé, il faut éxécuter les étapes suivantes dans l'ordre :

* Créer un fichier .env à la racine du projet en utilisant le fichier **.env.example** et renseigner chacun des champs :
    - MYSQL_USER : l'utilisateur de la base de donnée MySQL
    - MYSQL_PASSWORD : le mot de passe de l'utilisateur
    - MYSQL_HOST : le host de MySQL
    - API_PASSWORD : un mot de passe lié à l'API. Sert à simuler la connexion d'un utilisateur enregistré dans la version 0.1.0 pour générer un token
    - SECRET_KEY : clé secrète (à définir aléatoirement) servant à générer les tokens
    - FOOTBALL_DATA_API_KEY : clé d'accès à l'API Football-data (il faut créer un compte utilisateur au préalable)

* Il faut ensuite éxécuter les scripts d'extraction des données :
```console
python football_data_api.py
python wikipedia_webscrap.py
```
Cela va créer un ensemble de fichiers dans le dossier data à la racine du projet. Ces fichiers JSON et CSV contiennent l'ensemble des données non nettoyées qui vont servir à créer la base de donnée.

* Ensuite, il faut se connecter à MySQL depuis une console et créer les tables de la base de donnée MySQL avec le script SQL dédié :
```sql
source ./src/football_bdd.sql
```

* Enfin on éxécute le script data_cleaning_insertion.py qui va nettoyer les données, les agréger et les enrichir puis les insérer dans les bases MySQL et MongoDB

## Lancement de l'API
Une fois la base de donnée remplie, on peut lancer localement l'API avec la commande suivante, depuis l'environnement virtuel et en étant situé à la racine du projet :
```console
fastapi dev app.py
```

L'API est alors accessible depuis la documentation OpenAPI à l'adresse https://127.0.0.1:8000/docs
