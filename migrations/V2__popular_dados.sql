-- V2__popular_dados.sql
INSERT INTO lancamento (descricao, data_lancamento, valor, tipo_lancamento, situacao) VALUES
('Salário Mensal',    '2024-01-05', 5000.00, 'R', 'E'),
('Aluguel',           '2024-01-10', 1200.00, 'D', 'E'),
('Supermercado',      '2024-01-12',  450.00, 'D', 'E'),
('Freelance Design',  '2024-01-15',  800.00, 'R', 'E'),
('Conta de Luz',      '2024-01-18',  180.00, 'D', 'P'),
('Academia',          '2024-01-20',   99.90, 'D', 'E'),
('Venda de Produto',  '2024-01-22',  350.00, 'R', 'E'),
('Internet',          '2024-01-25',   89.90, 'D', 'P'),
('Restaurante',       '2024-02-01',   75.50, 'D', 'E'),
('Consultoria',       '2024-02-05', 1200.00, 'R', 'P')
ON CONFLICT DO NOTHING;
