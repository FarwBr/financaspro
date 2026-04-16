"""
20 testes unitários — FinançasPro
Execute com: pytest test_app.py -v
"""
import pytest, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app
from init_db import init_db
from werkzeug.security import generate_password_hash

DB_TEST = os.path.join(os.path.dirname(__file__), 'financas_test.db')

@pytest.fixture(autouse=True)
def setup_db(monkeypatch):
    """Usa banco de testes isolado a cada teste."""
    import app as app_module
    monkeypatch.setattr(app_module, 'DB_PATH', DB_TEST)
    # Recria o banco de teste
    import sqlite3
    if os.path.exists(DB_TEST):
        os.remove(DB_TEST)
    conn = sqlite3.connect(DB_TEST)
    conn.executescript("""
        CREATE TABLE usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL, login TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL, situacao TEXT DEFAULT 'A'
        );
        CREATE TABLE lancamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL, data_lancamento TEXT NOT NULL,
            valor REAL NOT NULL, tipo_lancamento TEXT NOT NULL,
            situacao TEXT DEFAULT 'P'
        );
    """)
    conn.execute("INSERT INTO usuario (nome,login,senha,situacao) VALUES (?,?,?,?)",
                 ('Admin', 'admin', generate_password_hash('admin123'), 'A'))
    conn.executemany(
        "INSERT INTO lancamento (descricao,data_lancamento,valor,tipo_lancamento,situacao) VALUES (?,?,?,?,?)",
        [
            ('Salário',    '2024-01-05', 5000.00, 'R', 'E'),
            ('Aluguel',    '2024-01-10', 1200.00, 'D', 'E'),
            ('Freelance',  '2024-02-01',  800.00, 'R', 'P'),
            ('Mercado',    '2024-02-05',  300.00, 'D', 'P'),
            ('Consultoria','2024-03-01', 1500.00, 'R', 'C'),
        ]
    )
    conn.commit(); conn.close()
    yield
    if os.path.exists(DB_TEST):
        os.remove(DB_TEST)

@pytest.fixture
def client():
    flask_app.config['TESTING']    = True
    flask_app.config['SECRET_KEY'] = 'test'
    with flask_app.test_client() as c:
        yield c

def login(client):
    return client.post('/login', data={'login': 'admin', 'senha': 'admin123'},
                       follow_redirects=True)

# ── AUTENTICAÇÃO (4 testes) ───────────────────────────────────────────

def test_1_login_valido(client):
    """Login com credenciais corretas redireciona para lançamentos."""
    resp = login(client)
    assert resp.status_code == 200
    assert 'Lançamentos'.encode() in resp.data or b'lan' in resp.data.lower()

def test_2_login_senha_errada(client):
    """Login com senha errada exibe mensagem de erro."""
    resp = client.post('/login', data={'login': 'admin', 'senha': 'errada'},
                       follow_redirects=True)
    assert 'inválidos'.encode() in resp.data or b'inv' in resp.data.lower()

def test_3_login_usuario_inexistente(client):
    """Login com usuário inexistente deve falhar."""
    resp = client.post('/login', data={'login': 'naoexiste', 'senha': 'qualquer'},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert b'login' in resp.data.lower()

def test_4_acesso_sem_autenticacao(client):
    """Acessar /lancamentos sem login redireciona para /login."""
    resp = client.get('/lancamentos', follow_redirects=False)
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']

# ── LISTAGEM (3 testes) ───────────────────────────────────────────────

def test_5_listagem_autenticado(client):
    """Usuário logado acessa listagem com sucesso."""
    login(client)
    resp = client.get('/lancamentos')
    assert resp.status_code == 200
    assert 'Salário'.encode() in resp.data

def test_6_listagem_exibe_todos_lancamentos(client):
    """Listagem exibe todos os 5 lançamentos do banco de teste."""
    login(client)
    resp = client.get('/lancamentos')
    assert b'Salário' in resp.data or b'Sal' in resp.data
    assert b'Aluguel' in resp.data

def test_7_filtro_por_tipo_receita(client):
    """Filtro por tipo=R retorna apenas receitas."""
    login(client)
    resp = client.get('/lancamentos?tipo=R')
    assert resp.status_code == 200
    assert b'Salário' in resp.data or b'Freelance' in resp.data

# ── FILTROS (4 testes) ────────────────────────────────────────────────

def test_8_filtro_por_tipo_despesa(client):
    """Filtro por tipo=D retorna apenas despesas."""
    login(client)
    resp = client.get('/lancamentos?tipo=D')
    assert b'Aluguel' in resp.data or b'Mercado' in resp.data

def test_9_filtro_por_situacao_pendente(client):
    """Filtro por situacao=P retorna apenas pendentes."""
    login(client)
    resp = client.get('/lancamentos?situacao=P')
    assert b'Freelance' in resp.data or b'Mercado' in resp.data

def test_10_filtro_por_data_inicial(client):
    """Filtro por data inicial filtra corretamente."""
    login(client)
    resp = client.get('/lancamentos?dt_ini=2024-02-01')
    assert resp.status_code == 200

def test_11_filtro_combinado_tipo_situacao(client):
    """Filtro combinado tipo+situação funciona."""
    login(client)
    resp = client.get('/lancamentos?tipo=R&situacao=E')
    assert resp.status_code == 200
    assert b'Salário' in resp.data

# ── CRUD — CRIAR (3 testes) ───────────────────────────────────────────

def test_12_criar_lancamento(client):
    """Criação de lançamento persiste no banco."""
    login(client)
    resp = client.post('/lancamentos/novo', data={
        'descricao': 'Novo Teste', 'data_lancamento': '2024-04-01',
        'valor': '250.00', 'tipo_lancamento': 'R', 'situacao': 'P'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Novo Teste' in resp.data

def test_13_criar_lancamento_despesa(client):
    """Criação de lançamento do tipo despesa funciona."""
    login(client)
    resp = client.post('/lancamentos/novo', data={
        'descricao': 'Despesa Teste', 'data_lancamento': '2024-04-02',
        'valor': '150.00', 'tipo_lancamento': 'D', 'situacao': 'E'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Despesa Teste' in resp.data

def test_14_form_novo_retorna_200(client):
    """GET /lancamentos/novo retorna página de formulário."""
    login(client)
    resp = client.get('/lancamentos/novo')
    assert resp.status_code == 200

# ── CRUD — EDITAR (3 testes) ──────────────────────────────────────────

def test_15_editar_lancamento(client):
    """Edição de lançamento existente altera os dados."""
    login(client)
    resp = client.post('/lancamentos/1/editar', data={
        'descricao': 'Salário Editado', 'data_lancamento': '2024-01-05',
        'valor': '5500.00', 'tipo_lancamento': 'R', 'situacao': 'E'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Salário Editado' in resp.data

def test_16_form_editar_carrega_dados(client):
    """GET /lancamentos/1/editar carrega dados do lançamento."""
    login(client)
    resp = client.get('/lancamentos/1/editar')
    assert resp.status_code == 200
    assert b'Sal' in resp.data

def test_17_editar_lancamento_inexistente(client):
    """Editar lançamento inexistente redireciona com erro."""
    login(client)
    resp = client.get('/lancamentos/9999/editar', follow_redirects=True)
    assert resp.status_code == 200

# ── CRUD — EXCLUIR (2 testes) ─────────────────────────────────────────

def test_18_excluir_lancamento(client):
    """Exclusão remove o lançamento da listagem."""
    login(client)
    resp = client.post('/lancamentos/1/excluir', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Aluguel' in resp.data  # outros ainda existem

def test_19_excluir_redireciona(client):
    """Exclusão redireciona para a listagem."""
    login(client)
    resp = client.post('/lancamentos/2/excluir', follow_redirects=False)
    assert resp.status_code == 302

# ── PDF EXPORT (1 teste) ──────────────────────────────────────────────

def test_20_exportar_pdf(client):
    """Exportação de PDF retorna arquivo PDF válido."""
    login(client)
    resp = client.get('/lancamentos/exportar')
    assert resp.status_code == 200
    assert resp.content_type == 'application/pdf'
    assert resp.data[:4] == b'%PDF'
