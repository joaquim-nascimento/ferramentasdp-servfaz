CREATE DATABASE IF NOT EXISTS ferias_db;
USE ferias_db;

CREATE TABLE IF NOT EXISTS Employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    admissionDate DATE NOT NULL,
    registration VARCHAR(50) NOT NULL UNIQUE,
    contractNumber VARCHAR(50) NOT NULL,
    lastVacationDate DATE,
    vacationDays INT DEFAULT 30,
    absenceDays INT DEFAULT 0,
    absence VARCHAR(150) NOT NULL,
    isEligible BOOLEAN DEFAULT TRUE,
    createdAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_contract (contractNumber),
    INDEX idx_eligible (isEligible)
);

SELECT * FROM Employees;

CREATE TABLE IF NOT EXISTS Vacations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employeeId INT NOT NULL,
    startDate DATE NOT NULL,
    endDate DATE NOT NULL,
    days INT NOT NULL,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    createdAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updatedAt DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (employeeId) REFERENCES Employees(id) ON DELETE CASCADE,
    
    INDEX idx_start_date (startDate),
    INDEX idx_end_date (endDate),
    INDEX idx_status (status)
);

SELECT * FROM Vacations;

DELIMITER //
CREATE TRIGGER before_employee_insert_update
BEFORE INSERT ON Employees
FOR EACH ROW
BEGIN
    DECLARE months_worked INT;
    DECLARE total_days_worked INT;
    
    SET months_worked = TIMESTAMPDIFF(MONTH, NEW.admissionDate, CURDATE());
    
    IF months_worked >= 12 AND NEW.absenceDays < 180 THEN
        SET NEW.isEligible = TRUE;
    ELSE
        SET NEW.isEligible = FALSE;
    END IF;
END//
DELIMITER ;