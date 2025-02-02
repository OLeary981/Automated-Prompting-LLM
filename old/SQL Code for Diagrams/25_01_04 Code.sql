-- Drop existing tables if they exist
DROP DATABASE IF EXISTS prototype_test_25_01_02;
CREATE DATABASE prototype_test_25_01_02;
USE prototype_test_25_01_02;


-- Create independent tables first
CREATE TABLE provider (
    provider_id INTEGER AUTO_INCREMENT PRIMARY KEY,
    provider_name TEXT NOT NULL    
);

CREATE TABLE IF NOT EXISTS `model` (
    model_id INTEGER AUTO_INCREMENT PRIMARY KEY, 
    model_name TEXT NOT NULL,
    provider_id INTEGER NOT NULL,
    endpoint TEXT,
    request_delay FLOAT NOT NULL,
    parameters TEXT NOT NULL,
    FOREIGN KEY (provider_id) REFERENCES provider (provider_id)    
);


CREATE TABLE IF NOT EXISTS question (
    question_id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS template (
    template_id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS `word` (
    word_id INT AUTO_INCREMENT PRIMARY KEY,
    `word` VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS category (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS `field` (
    field_id INT AUTO_INCREMENT PRIMARY KEY,
    field_name VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS story (
    story_id INT AUTO_INCREMENT PRIMARY KEY,
    content LONGTEXT NOT NULL,
    template_id INT,
    FOREIGN KEY (template_id) REFERENCES template (template_id)
);

-- Create tables with dependencies
CREATE TABLE IF NOT EXISTS word_field (
    word_id INT NOT NULL,
    field_id INT NOT NULL,
    PRIMARY KEY (word_id, field_id),
    FOREIGN KEY (word_id) REFERENCES `word` (word_id) ON DELETE CASCADE,
    FOREIGN KEY (field_id) REFERENCES `field` (field_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS story_category (
    story_id INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (story_id, category_id),
    FOREIGN KEY (story_id) REFERENCES story (story_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES category (category_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS prompt (
    prompt_id INT AUTO_INCREMENT PRIMARY KEY,
    model_id INTEGER NOT NULL,
    temperature REAL NOT NULL,
    max_tokens INTEGER NOT NULL,
    top_p REAL NOT NULL,
    story_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    payload LONGTEXT NOT NULL,    
    FOREIGN KEY (story_id) REFERENCES story(story_id),
    FOREIGN KEY (question_id) REFERENCES question(question_id),
    FOREIGN KEY (model_id) REFERENCES model(model_id)
);

CREATE TABLE IF NOT EXISTS response (
    response_id INT AUTO_INCREMENT PRIMARY KEY,
    prompt_id INT NOT NULL,
    response_content TEXT NOT NULL,
    full_response TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES prompt (prompt_id)
);
