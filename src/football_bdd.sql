DROP DATABASE IF EXISTS football_predictor;
CREATE DATABASE IF NOT EXISTS football_predictor CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE football_predictor;

SELECT 'CREATING DATABASE STRUCTURE' as 'INFO';

DROP TABLE IF EXISTS Player,
                     Staff,
                     Ranking,
                     Team,
                     Referee,
                     League;

/*!50503 set default_storage_engine = InnoDB */;
/*!50503 select CONCAT('storage engine: ', @@default_storage_engine) as INFO */;

CREATE TABLE `Team` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(255) NOT NULL,
    `shortname` VARCHAR(100) NOT NULL,
    `stadium` VARCHAR(100) NOT NULL,
    `founded` SMALLINT NOT NULL
);

CREATE TABLE `League` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(50) NOT NULL,
    `country` VARCHAR(30) NOT NULL,
    `season` SMALLINT NOT NULL
);

CREATE TABLE `Player` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `first_name` VARCHAR(50) NOT NULL,
    `last_name` VARCHAR(50) NOT NULL,
    `birthdate` DATE,
    `nationality` VARCHAR(100),
    `position` ENUM('Gardien', 'Defenseur', 'Milieu', 'Attaquant') NOT NULL,
    `team_id` INT NOT NULL DEFAULT 999,
    FOREIGN KEY (`team_id`) REFERENCES `Team` (`id`) ON UPDATE CASCADE ON DELETE SET DEFAULT
);

CREATE TABLE `Staff` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `first_name` VARCHAR(50) NOT NULL,
    `last_name` VARCHAR(50) NOT NULL,
    `birthdate` DATE,
    `nationality` VARCHAR(100),
    `role` ENUM('Entraineur', 'Entraineur des gardiens', 'Adjoint', 'Preparateur physique') NOT NULL,
    `team_id` INT NOT NULL DEFAULT 999,
    FOREIGN KEY (`team_id`) REFERENCES `Team` (`id`) ON UPDATE CASCADE ON DELETE SET DEFAULT
);

CREATE TABLE `Referee` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `first_name` VARCHAR(50) NOT NULL,
    `last_name` VARCHAR(50) NOT NULL,
    `birthdate` DATE,
    `nationality` VARCHAR(100)
);

CREATE TABLE `Ranking` (
    `team_id` INT NOT NULL DEFAULT 999,
    `league_id` INT NOT NULL,
    `type` ENUM('HOME', 'AWAY', 'TOTAL') NOT NULL,
    `start_date` DATE NOT NULL DEFAULT '1990-09-24',
    `end_date` DATE NOT NULL DEFAULT '1990-09-25',
    `position` SMALLINT NOT NULL DEFAULT 0,
    `points` SMALLINT NOT NULL DEFAULT 0,
    `played` SMALLINT NOT NULL DEFAULT 0,
    `goals_for` SMALLINT NOT NULL DEFAULT 0,
    `goals_against` SMALLINT NOT NULL DEFAULT 0,
    `won` SMALLINT NOT NULL DEFAULT 0,
    `draw` SMALLINT NOT NULL DEFAULT 0,
    `lost` SMALLINT NOT NULL DEFAULT 0,
    FOREIGN KEY (`team_id`) REFERENCES `Team` (`id`) ON UPDATE CASCADE ON DELETE SET DEFAULT,
    FOREIGN KEY (`league_id`) REFERENCES `League` (`id`) ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY (`team_id`, `league_id`, `type`)
);

flush /*!50503 binary */ logs;