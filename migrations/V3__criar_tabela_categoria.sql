-- V3__criar_tabela_categoria.sql
CREATE TABLE IF NOT EXISTS categoria (
    id       SERIAL PRIMARY KEY,
    nome     VARCHAR(100) NOT NULL UNIQUE,
    cor      VARCHAR(7)   NOT NULL DEFAULT '#888888',
    situacao VARCHAR(1)   NOT NULL DEFAULT 'A'
);
INSERT INTO categoria (nome, cor) VALUES
    ('Alimentacao',  '#FF6B6B'),
    ('Moradia',      '#4ECDC4'),
    ('Transporte',   '#45B7D1'),
    ('Salario',      '#00C896')
ON CONFLICT DO NOTHING;
