-- Finance Tracker Database Setup
-- Create database
CREATE DATABASE IF NOT EXISTS finance_tracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE finance_tracker;

-- Create user (optional, for security)
-- CREATE USER 'finance_user'@'localhost' IDENTIFIED BY 'secure_password';
-- GRANT ALL PRIVILEGES ON finance_tracker.* TO 'finance_user'@'localhost';
-- FLUSH PRIVILEGES;

-- Create transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type ENUM('income', 'expense') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description VARCHAR(200) NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type (type),
    INDEX idx_category (category),
    INDEX idx_date (date),
    INDEX idx_created_at (created_at)
);

-- Create categories table
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    type ENUM('income', 'expense') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_category_type (name, type)
);

-- Create budgets table
CREATE TABLE IF NOT EXISTS budgets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    month INT NOT NULL CHECK (month >= 1 AND month <= 12),
    year INT NOT NULL CHECK (year >= 2020),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_budget_period (category, month, year),
    INDEX idx_period (month, year)
);

-- Insert default categories
INSERT IGNORE INTO categories (name, type) VALUES
-- Income categories
('Salary', 'income'),
('Freelance', 'income'),
('Investment', 'income'),
('Gift', 'income'),
('Other Income', 'income'),

-- Expense categories
('Food', 'expense'),
('Transportation', 'expense'),
('Entertainment', 'expense'),
('Bills', 'expense'),
('Shopping', 'expense'),
('Healthcare', 'expense'),
('Other Expense', 'expense');

-- Insert sample data (optional)
INSERT INTO transactions (type, amount, category, description, date) VALUES
('income', 5000.00, 'Salary', 'Monthly Salary', '2024-01-01'),
('expense', 800.00, 'Food', 'Groceries and dining', '2024-01-02'),
('expense', 200.00, 'Transportation', 'Gas and maintenance', '2024-01-03'),
('income', 1500.00, 'Freelance', 'Web development project', '2024-01-05'),
('expense', 150.00, 'Entertainment', 'Movies and games', '2024-01-06'),
('expense', 300.00, 'Bills', 'Electricity and internet', '2024-01-07'),
('expense', 250.00, 'Shopping', 'Clothes and accessories', '2024-01-10'),
('income', 2000.00, 'Investment', 'Stock dividends', '2024-01-15'),
('expense', 100.00, 'Healthcare', 'Doctor visit', '2024-01-18'),
('expense', 50.00, 'Other Expense', 'Miscellaneous', '2024-01-20');

-- Insert sample budgets
INSERT INTO budgets (category, amount, month, year) VALUES
('Food', 1000.00, 1, 2024),
('Transportation', 300.00, 1, 2024),
('Entertainment', 200.00, 1, 2024),
('Bills', 500.00, 1, 2024),
('Shopping', 400.00, 1, 2024),
('Healthcare', 200.00, 1, 2024);

-- Create views for reporting
CREATE OR REPLACE VIEW monthly_summary AS
SELECT 
    YEAR(date) as year,
    MONTH(date) as month,
    type,
    SUM(amount) as total_amount,
    COUNT(*) as transaction_count
FROM transactions 
GROUP BY YEAR(date), MONTH(date), type
ORDER BY year DESC, month DESC;

CREATE OR REPLACE VIEW category_summary AS
SELECT 
    category,
    type,
    SUM(amount) as total_amount,
    COUNT(*) as transaction_count,
    AVG(amount) as avg_amount
FROM transactions 
GROUP BY category, type
ORDER BY total_amount DESC;

-- Create stored procedures for common operations
DELIMITER //

CREATE PROCEDURE GetMonthlyReport(IN report_year INT, IN report_month INT)
BEGIN
    SELECT 
        category,
        type,
        SUM(amount) as total,
        COUNT(*) as count
    FROM transactions 
    WHERE YEAR(date) = report_year AND MONTH(date) = report_month
    GROUP BY category, type
    ORDER BY type, total DESC;
END //

CREATE PROCEDURE GetBudgetStatus(IN budget_month INT, IN budget_year INT)
BEGIN
    SELECT 
        b.category,
        b.amount as budget_amount,
        COALESCE(t.spent_amount, 0) as spent_amount,
        (b.amount - COALESCE(t.spent_amount, 0)) as remaining,
        CASE 
            WHEN b.amount > 0 THEN (COALESCE(t.spent_amount, 0) / b.amount) * 100 
            ELSE 0 
        END as percentage_used
    FROM budgets b
    LEFT JOIN (
        SELECT 
            category, 
            SUM(amount) as spent_amount
        FROM transactions 
        WHERE type = 'expense' 
            AND MONTH(date) = budget_month 
            AND YEAR(date) = budget_year
        GROUP BY category
    ) t ON b.category = t.category
    WHERE b.month = budget_month AND b.year = budget_year
    ORDER BY percentage_used DESC;
END //

DELIMITER ;

-- Show table structure
SHOW TABLES;
DESCRIBE transactions;
DESCRIBE categories;
DESCRIBE budgets;