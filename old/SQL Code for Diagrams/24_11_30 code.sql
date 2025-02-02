-- Create the database
CREATE DATABASE IF NOT EXISTS prototype_test_24_11_30;
USE prototype_test_24_11_30;

-- Create the `stories` table
CREATE TABLE IF NOT EXISTS stories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL
);

-- Create the `questions` table
CREATE TABLE IF NOT EXISTS questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL
);

-- Create the `story_templates` table
CREATE TABLE IF NOT EXISTS story_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    template TEXT NOT NULL
);

-- Create the `prompt_tests` table
CREATE TABLE IF NOT EXISTS prompt_tests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    provider VARCHAR(255) NOT NULL,
    model VARCHAR(255) NOT NULL,
    temperature FLOAT NOT NULL,
    max_tokens INT NOT NULL,
    top_p FLOAT NOT NULL,
    story_id INT NOT NULL,
    question_id INT NOT NULL,
    payload TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES stories(id),
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

-- Create the `responses` table
CREATE TABLE IF NOT EXISTS responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prompt_test_id INT NOT NULL,
    response_content TEXT NOT NULL,
    full_response TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_test_id) REFERENCES prompt_tests(id)
);

-- Create the `words` table
CREATE TABLE IF NOT EXISTS words (
    id INT AUTO_INCREMENT PRIMARY KEY,
    word VARCHAR(255) NOT NULL UNIQUE
);

-- Create the `categories` table
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL UNIQUE
);

-- Create the `word_categories` table
CREATE TABLE IF NOT EXISTS word_categories (
    word_id INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (word_id, category_id),
    FOREIGN KEY (word_id) REFERENCES words (id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
);

-- Insert words
INSERT INTO words (word) VALUES 
('France'),
('Spain'),
('man'),
('dog'),
('cat'),
('ball'),
('hat'),
('shiny'),
('red'),
('running'),
('falling');

-- Insert categories
INSERT INTO categories (category_name) VALUES 
('country'),
('character'),
('object'),
('adjective'),
('verb');

-- Insert word-category relationships
INSERT INTO word_categories (word_id, category_id)
SELECT w.id, c.id FROM words w, categories c WHERE 
(w.word = 'France' AND c.category_name = 'country') OR
(w.word = 'Spain' AND c.category_name = 'country') OR
(w.word = 'man' AND c.category_name = 'character') OR
(w.word = 'dog' AND c.category_name = 'character') OR
(w.word = 'cat' AND c.category_name = 'character') OR
(w.word = 'ball' AND c.category_name = 'object') OR
(w.word = 'hat' AND c.category_name = 'object') OR
(w.word = 'running' AND c.category_name = 'verb') OR
(w.word = 'falling' AND c.category_name = 'verb');
