CREATE TABLE departments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);


CREATE TABLE sender_aliases (
    id INT AUTO_INCREMENT PRIMARY KEY,
    alias VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255) NOT NULL,
    department_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
);
CREATE INDEX idx_sender_aliases_alias ON sender_aliases(alias);


CREATE TABLE jargons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    letter VARCHAR(10),
    word VARCHAR(255),
    definition TEXT,
    dialect VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    CREATE INDEX idx_jargons_word ON jargons(word);
    CREATE UNIQUE INDEX idx_unique_jargon ON jargons(word, dialect);
);


CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    role ENUM('super_admin', 'admin', 'user') DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE, 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);


CREATE TABLE summaries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_name VARCHAR(255),
    summary_text LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INT,
    CONSTRAINT fk_user_summary FOREIGN KEY (user_id) REFERENCES users(id)
);


CREATE TABLE tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(50) UNIQUE NOT NULL, -- e.g., 'TSK-20260303-009'
    task_description TEXT NOT NULL,
    department_name VARCHAR(100),         -- From JSON 'department'
    status ENUM('Pending', 'In Progress', 'Completed', 'Blocked') DEFAULT 'Pending',
    date_created DATE,
    possible_assignees TEXT,              -- Stores the list as a string/comma-separated
    completed_by VARCHAR(255) DEFAULT NULL,
    notes TEXT,                           -- Detailed context from the AI
    assigned_name VARCHAR(100) DEFAULT NULL -- For your UI manual insertion
);


CREATE TABLE ocr_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_name VARCHAR(255) UNIQUE NOT NULL,
    raw_json_data JSON NOT NULL, -- Stores the full output from the OCR
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary_id INT, -- Optional: Link to the summary if it already exists
    FOREIGN KEY (summary_id) REFERENCES summaries(id) ON DELETE SET NULL
);

