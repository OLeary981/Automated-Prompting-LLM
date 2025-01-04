-- Drop existing tables if they exist
DROP DATABASE IF EXISTS prototype_test_25_01_04;
CREATE DATABASE prototype_test_25_01_04;
USE prototype_test_25_01_04;


-- Create independent tables first
-- Question table
CREATE TABLE IF NOT EXISTS question (
    question_id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL
);

-- Template table
CREATE TABLE IF NOT EXISTS template (
    template_id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL
);

-- Story table
CREATE TABLE IF NOT EXISTS story (
    story_id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL,
    template_id INT,
    FOREIGN KEY (template_id) REFERENCES template (template_id)
);

-- Category table
CREATE TABLE IF NOT EXISTS category (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category TEXT NOT NULL
);

-- Story-Category relationship table
CREATE TABLE IF NOT EXISTS story_category (
    story_id INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (story_id, category_id),
    FOREIGN KEY (story_id) REFERENCES story (story_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES category (category_id) ON DELETE CASCADE
);

-- Provider table
CREATE TABLE provider (
    provider_id INT AUTO_INCREMENT PRIMARY KEY,
    provider_name TEXT NOT NULL    
);

-- Model table
CREATE TABLE IF NOT EXISTS model (
    model_id INT AUTO_INCREMENT PRIMARY KEY,
    name TEXT NOT NULL,
    provider_id INT NOT NULL,
    endpoint TEXT,
    request_delay REAL NOT NULL,
    parameters TEXT NOT NULL,
    FOREIGN KEY (provider_id) REFERENCES provider (provider_id)
);

-- Prompt table
CREATE TABLE IF NOT EXISTS prompt (
    prompt_id INT AUTO_INCREMENT PRIMARY KEY,
    model_id INT NOT NULL,
    temperature REAL,
    max_tokens INT,
    top_p REAL,
    story_id INT NOT NULL,
    question_id INT NOT NULL,
    payload LONGTEXT NOT NULL,    
    FOREIGN KEY (story_id) REFERENCES story (story_id),
    FOREIGN KEY (question_id) REFERENCES question (question_id),
    FOREIGN KEY (model_id) REFERENCES model (model_id)
);

-- Response table
CREATE TABLE IF NOT EXISTS response (
    response_id INT AUTO_INCREMENT PRIMARY KEY,
    prompt_id INT NOT NULL,
    response_content TEXT NOT NULL,
    full_response LONGTEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES prompt (prompt_id)
);

-- Word table
CREATE TABLE IF NOT EXISTS word (
    word_id INT AUTO_INCREMENT PRIMARY KEY,
    word TEXT NOT NULL,
    UNIQUE KEY (word(255))
);

-- Field table
CREATE TABLE IF NOT EXISTS field (
    field_id INT AUTO_INCREMENT PRIMARY KEY,
    field TEXT NOT NULL,
    UNIQUE KEY (field(255))
);

-- Word-Field relationship table
CREATE TABLE IF NOT EXISTS word_field (
    word_id INT NOT NULL,
    field_id INT NOT NULL,
    PRIMARY KEY (word_id, field_id),
    FOREIGN KEY (word_id) REFERENCES word (word_id) ON DELETE CASCADE,
    FOREIGN KEY (field_id) REFERENCES field (field_id) ON DELETE CASCADE
);
