CREATE TABLE `Apartamentos` (
  `Booking ID` varchar(255) NOT NULL,
  PRIMARY KEY (`Booking ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `bookings` (
  `ID` int NOT NULL AUTO_INCREMENT,
  `Booking ID` varchar(255) NOT NULL,
  `Nº Booking` varchar(255) DEFAULT NULL,
  `Nombre,Apellidos` varchar(100) NOT NULL,
  `Email` varchar(255) DEFAULT NULL,
  `Movil` varchar(100) DEFAULT NULL,
  `Check-In` date NOT NULL,
  `Check-Out` date NOT NULL,
  `Nº Noches` int DEFAULT NULL,
  `Status` varchar(100) DEFAULT NULL,
  `Nº Personas` int DEFAULT NULL,
  `Nº Adultos` int DEFAULT NULL,
  `Nº Niños` int DEFAULT NULL,
  `Precio` decimal(10, 2) DEFAULT NULL,
  `Comm y Cargos` decimal(10, 2) DEFAULT NULL,
  `Electric Allowance` smallint DEFAULT '0',
  PRIMARY KEY (`ID`),
  UNIQUE KEY `ID` (`ID`),
  KEY `fk_bookings_Apartamentos_Booking_ID` (`Booking ID`),
  CONSTRAINT `fk_bookings_Apartamentos_Booking_ID`
    FOREIGN KEY (`Booking ID`)
    REFERENCES `Apartamentos` (`Booking ID`)
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
