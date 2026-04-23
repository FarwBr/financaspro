-- V1__criar_tabelas.sql
CREATE TABLE IF NOT EXISTS usuario (
    id       SERIAL PRIMARY KEY,
    nome     VARCHAR(100) NOT NULL,
    login    VARCHAR(50)  NOT NULL UNIQUE,
    senha    VARCHAR(255) NOT NULL,
    situacao VARCHAR(1)   NOT NULL DEFAULT 'A' CHECK (situacao IN ('A','I'))
);

CREATE TABLE IF NOT EXISTS lancamento (
    id               SERIAL PRIMARY KEY,
    descricao        VARCHAR(200) NOT NULL,
    data_lancamento  DATE         NOT NULL,
    valor            NUMERIC(10,2) NOT NULL,
    tipo_lancamento  VARCHAR(1)   NOT NULL CHECK (tipo_lancamento IN ('R','D')),
    situacao         VARCHAR(1)   NOT NULL DEFAULT 'P' CHECK (situacao IN ('P','E','C'))
);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version     VARCHAR(50) PRIMARY KEY,
    applied_at  TIMESTAMP DEFAULT NOW()
);
