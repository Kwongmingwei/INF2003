
CREATE DATABASE IF NOT EXISTS `book_review` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_uca1400_ai_ci */;
USE `book_review`;

CREATE TABLE IF NOT EXISTS `author` (
  `author_id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `bio` text DEFAULT NULL,
  `birth_date` date DEFAULT NULL,
  PRIMARY KEY (`author_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS `author_work` (
  `author_id` int(11) NOT NULL,
  `work_id` int(11) NOT NULL,
  KEY `FK_author_work_author` (`author_id`) USING BTREE,
  KEY `FK_author_work_book_work` (`work_id`) USING BTREE,
  CONSTRAINT `FK_author_work_author` FOREIGN KEY (`author_id`) REFERENCES `author` (`author_id`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `FK_author_work_book_work` FOREIGN KEY (`work_id`) REFERENCES `book_work` (`work_id`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS `book_edition` (
  `work_id` int(11) DEFAULT NULL,
  `isbn13` char(13) NOT NULL,
  `isbn10` char(10) DEFAULT NULL,
  `publish_year` year(4) DEFAULT NULL,
  `cover_id` int(11) DEFAULT NULL,
  `publisher_name` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`isbn13`),
  UNIQUE KEY `isbn10` (`isbn10`),
  KEY `FK_book_edition_book_work` (`work_id`) USING BTREE,
  CONSTRAINT `FK_book_edition_book_work` FOREIGN KEY (`work_id`) REFERENCES `book_work` (`work_id`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS `book_work` (
  `work_id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(150) NOT NULL,
  `description` text DEFAULT NULL,
  `avg_rating` decimal(3,2) DEFAULT NULL,
  PRIMARY KEY (`work_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

CREATE TABLE IF NOT EXISTS `category` (
  `genre_id` int(11) NOT NULL,
  `work_id` int(11) NOT NULL,
  KEY `FK_category_genre` (`genre_id`),
  KEY `FK_category_book_work` (`work_id`) USING BTREE,
  CONSTRAINT `FK_category_book_work` FOREIGN KEY (`work_id`) REFERENCES `book_work` (`work_id`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `FK_category_genre` FOREIGN KEY (`genre_id`) REFERENCES `genre` (`genre_id`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;


CREATE TABLE IF NOT EXISTS `genre` (
  `genre_id` int(11) NOT NULL AUTO_INCREMENT,
  `genre_name` varchar(100) NOT NULL DEFAULT '',
  PRIMARY KEY (`genre_id`),
  UNIQUE KEY `genre_name` (`genre_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;


CREATE TABLE IF NOT EXISTS `user` (
  `user_id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) NOT NULL,
  `password` varchar(50) NOT NULL,
  `email` varchar(100) NOT NULL,
  `date_joined` date NOT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
