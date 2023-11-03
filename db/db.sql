-- MariaDB dump 10.19  Distrib 10.6.14-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: allsky
-- ------------------------------------------------------
-- Server version	10.6.14-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `config`
--

DROP TABLE IF EXISTS `config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `config` (
  `id` varchar(100) NOT NULL,
  `val` text NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `config`
--

LOCK TABLES `config` WRITE;
/*!40000 ALTER TABLE `config` DISABLE KEYS */;
INSERT INTO `config` VALUES ('archive','{\"jpg\":30,\"fit\":99,\"sensors\":100,\"mp4\":30}'),('ccd','{\"binning\":2,\"bits\":16,\"avgMin\":20000,\"avgMax\":40000,\"center\":50,\"expMin\":0.0001,\"expMax\":45,\"gainMin\":1,\"gainMax\":250,\"gainStep\":50}'),('observatory','{\"name\":\"My Observatory\",\"lat\":40.40,\"lon\":50.50,\"timezone\":3}'),('processing','{\"crop\":{\"left\":0,\"right\":0,\"top\":0,\"bottom\":0},\"logo\":{\"x\":0,\"y\":0},\"annotation\":[{\"type\":\"datetime\",\"x\":\"3\",\"y\":\"3\",\"size\":\"40\",\"color\":\"rgb(127, 127, 127)\",\"format\":\"%Y-%m-%d\"},{\"type\":\"datetime\",\"x\":\"3\",\"y\":\"50\",\"size\":\"40\",\"color\":\"rgb(135, 135, 135)\",\"format\":\"%H:%M\"},{\"type\":\"stars\",\"x\":\"0\",\"y\":\"100\",\"size\":\"40\",\"color\":\"rgb(129, 129, 129)\",\"format\":\"{} stars\"},{\"type\":\"yolo-clear\",\"x\":\"3\",\"y\":\"990\",\"size\":\"40\",\"color\":\"rgb(182, 182, 182)\",\"format\":\"AI {}%\"}],\"wb\":{\"type\":\"gain\",\"r\":\"8\",\"g\":\"1.2\",\"b\":\"0.9\"},\"sd\":{\"enable\":true,\"fwhm\":1.5,\"threshold\":1},\"yolo\":{\"enable\":false},\"transpose\":3}'),('publish','{\"jpg\":\"https://allsky.milantiev.com/publish/jpg\"}'),('relays','[]'),('sensors','{\"bme280\":[{\"name\":\"\"},{\"name\":\"\"}],\"ads1115\":[{\"name\":\"\",\"divider\":\"\"},{\"name\":\"\",\"divider\":\"\"}]}'),('web','{\"counter\":\"\"}');
/*!40000 ALTER TABLE `config` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `relay`
--

DROP TABLE IF EXISTS `relay`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `relay` (
  `id` varchar(100) NOT NULL,
  `state` tinyint(1) NOT NULL,
  `date` int(10) unsigned NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `relay`
--

LOCK TABLES `relay` WRITE;
/*!40000 ALTER TABLE `relay` DISABLE KEYS */;
/*!40000 ALTER TABLE `relay` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sensor`
--

DROP TABLE IF EXISTS `sensor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sensor` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `type` enum('temperature','humidity','pressure','voltage','wind-speed','wind-direction','sky-temperature','ccd-exposure','ccd-average','ccd-gain','ccd-bin','stars-count','ai-clear','ai-cloud') NOT NULL,
  `channel` int(10) unsigned NOT NULL,
  `date` int(10) unsigned NOT NULL,
  `val` double NOT NULL,
  PRIMARY KEY (`id`),
  KEY `channel_type_date` (`channel`,`type`,`date`),
  KEY `type` (`type`)
) ENGINE=InnoDB AUTO_INCREMENT=263861 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sensor`
--

/*!40000 ALTER TABLE `sensor` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sensor_last`
--

DROP TABLE IF EXISTS `sensor_last`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sensor_last` (
  `type` enum('temperature','humidity','pressure','voltage','wind-speed','wind-direction','sky-temperature','ccd-exposure','ccd-average','ccd-gain','ccd-bin','stars-count','ai-clear','ai-cloud') NOT NULL,
  `channel` int(10) unsigned NOT NULL,
  `date` int(10) unsigned NOT NULL,
  `val` double NOT NULL,
  PRIMARY KEY (`type`,`channel`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sensor_last`
--

LOCK TABLES `sensor_last` WRITE;
/*!40000 ALTER TABLE `sensor_last` DISABLE KEYS */;
/*!40000 ALTER TABLE `sensor_last` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `password` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user`
--

LOCK TABLES `user` WRITE;
/*!40000 ALTER TABLE `user` DISABLE KEYS */;
INSERT INTO `user` VALUES (1,'admin','admin','admin');
/*!40000 ALTER TABLE `user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `video`
--

DROP TABLE IF EXISTS `video`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `video` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `job` varchar(100) NOT NULL,
  `work_queue` int(10) unsigned NOT NULL,
  `work_begin` int(10) unsigned NOT NULL,
  `work_end` int(10) unsigned NOT NULL,
  `video_begin` int(10) unsigned NOT NULL,
  `video_end` int(10) unsigned NOT NULL,
  `frames` int(10) unsigned NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `video`
--

LOCK TABLES `video` WRITE;
/*!40000 ALTER TABLE `video` DISABLE KEYS */;
/*!40000 ALTER TABLE `video` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-11-03 15:27:22
