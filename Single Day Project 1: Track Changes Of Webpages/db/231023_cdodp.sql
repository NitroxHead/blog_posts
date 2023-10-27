-- phpMyAdmin SQL Dump

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `231023_cdodp`
--

-- --------------------------------------------------------

--
-- Table structure for table `Categories`
--

CREATE TABLE `Categories` (
  `category_id` int NOT NULL,
  `category_name` varchar(50) NOT NULL,
  `change_action` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `Change_History`
--

CREATE TABLE `Change_History` (
  `change_id` int NOT NULL,
  `website_id` int DEFAULT NULL,
  `change_timestamp` datetime NOT NULL,
  `previous_hash` varchar(64) NOT NULL,
  `current_hash` varchar(64) NOT NULL,
  `change_details` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `Websites`
--

CREATE TABLE `Websites` (
  `website_id` int NOT NULL,
  `url` varchar(255) NOT NULL,
  `last_checked` datetime DEFAULT NULL,
  `hash` varchar(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `Website_Categories`
--

CREATE TABLE `Website_Categories` (
  `website_id` int NOT NULL,
  `category_id` int NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `Categories`
--
ALTER TABLE `Categories`
  ADD PRIMARY KEY (`category_id`);

--
-- Indexes for table `Change_History`
--
ALTER TABLE `Change_History`
  ADD PRIMARY KEY (`change_id`),
  ADD KEY `website_id` (`website_id`);

--
-- Indexes for table `Websites`
--
ALTER TABLE `Websites`
  ADD PRIMARY KEY (`website_id`);

--
-- Indexes for table `Website_Categories`
--
ALTER TABLE `Website_Categories`
  ADD PRIMARY KEY (`website_id`,`category_id`),
  ADD KEY `category_id` (`category_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `Categories`
--
ALTER TABLE `Categories`
  MODIFY `category_id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `Change_History`
--
ALTER TABLE `Change_History`
  MODIFY `change_id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `Websites`
--
ALTER TABLE `Websites`
  MODIFY `website_id` int NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `Change_History`
--
ALTER TABLE `Change_History`
  ADD CONSTRAINT `Change_History_ibfk_1` FOREIGN KEY (`website_id`) REFERENCES `Websites` (`website_id`);

--
-- Constraints for table `Website_Categories`
--
ALTER TABLE `Website_Categories`
  ADD CONSTRAINT `Website_Categories_ibfk_1` FOREIGN KEY (`website_id`) REFERENCES `Websites` (`website_id`),
  ADD CONSTRAINT `Website_Categories_ibfk_2` FOREIGN KEY (`category_id`) REFERENCES `Categories` (`category_id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
