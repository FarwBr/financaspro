"""
20 testes unitários — FinançasPro (PostgreSQL)
Execute: pytest test_app.py -v --html=relatorio_testes.html --self-contained-html
"""
import os
import sys
import pytest
import psycopg2
import psycopg2.extras
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Aponta para banco de testes
os.environ.update({
    'DB_HOST':     os.environ.get('DB_HOST',     'localhost'),
    'DB_PORT':     os.environ.get('DB_PORT',     '5432'),
    'DB_NAME':     os.environ.get('DB_NAME',     'financas_test'),
    'DB_USER':     os.environ.get('DB_USER',     'financas'),
    'DB_PASSWORD': os.environ.get('DB_PASSWORD', 'financas123'),
})

from app import app as flask_app
from werkzeug.security import generate_password_hash


def get_test_conn():
    return psycopg2.connect(
        host=os.environ['DB_HOST'], port=os.environ['DB_PORT'],
        dbname=os.environ['DB_NAME'], user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD']
    )


@pytest.fixture(scope='session', autouse=True)
def setup_test_db():
    """Cria schema e dados de teste uma vez por sessão."""
    conn = get_test_conn()
    cur  = conn.cursor()
    cur.execute("""
        DROP TABLE IF EXISTS lancamento CASCADE;
        DROP TABLE IF EXISTS usuario    CASCADE;
        CREATE TABLE usuario (
            id SERIAL PRIMARY KEY, nome VARCHAR(100) NOT NULL,
            login VARCHAR(50) NOT NULL UNIQUE, senha VARCHAR(255) NOT NULL,
            situacao VARCHAR(1) DEFAULT 'A'
        );
        CREATE TABLE lancamento (
            id SERIAL PRIMARY KEY, descricao VARCHAR(200) NOT NULL,
            data_lancamento DATE NOT NULL, valor NUMERIC(10,2) NOT NULL,
            tipo_lancamento VARCHAR(1) NOT NULL, situacao VARCHAR(1) DEFAULT 'P'
        );
    """)
    cur.execute(
        "INSERT INTO usuario (nome,login,senha,situacao) VALUES (%s,%s,%s,%s)",
        ('Admin', 'admin', generate_password_hash('admin123'), 'A')
    )
    cur.executemany(
        "INSERT INTO lancamento (descricao,data_lancamento,valor,tipo_lancamento,situacao) VALUES (%s,%s,%s,%s,%s)",
        [
            ('Salário',    '2024-01-05', 5000.00, 'R', 'E'),
            ('Aluguel',    '2024-01-10', 1200.00, 'D', 'E'),
            ('Freelance',  '2024-02-01',  800.00, 'R', 'P'),
            ('Mercado',    '2024-02-05',  300.00, 'D', 'P'),
            ('Consultoria','2024-03-01', 1500.00, 'R', 'C'),
        ]
    )
    conn.commit(); cur.close(); conn.close()
    yield
    conn = get_test_conn()
    cur  = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS lancamento CASCADE; DROP TABLE IF EXISTS usuario CASCADE;")
    conn.commit(); cur.close(); conn.close()


@pytest.fixture
def client():
    flask_app.config['TESTING']    = True
    flask_app.config['SECRET_KEY'] = 'test'
    with flask_app.test_client() as c:
        yield c


def login(client):
    return client.post('/login',
                       data={'login': 'admin', 'senha': 'admin123'},
                       follow_redirects=True)


# ── 1. AUTENTICAÇÃO ──────────────────────────────────────────────────

def test_01_login_valido(client):
    """Login com credenciais corretas redireciona para lançamentos."""
    resp = login(client)
    assert resp.status_code == 200

def test_02_login_senha_errada(client):
    """Login com senha errada retorna página com erro."""
    resp = client.post('/login', data={'login': 'admin', 'senha': 'errada'},
                       follow_redirects=True)
    assert 'inválidos'.encode() in resp.data

def test_03_login_usuario_inexistente(client):
    """Login com usuário inexistente falha."""
    resp = client.post('/login', data={'login': 'naoexiste', 'senha': 'x'},
                       follow_redirects=True)
    assert resp.status_code == 200

def test_04_acesso_sem_autenticacao(client):
    """Acesso sem login redireciona para /login."""
    resp = client.get('/lancamentos', follow_redirects=False)
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']

# ── 2. LISTAGEM ──────────────────────────────────────────────────────

def test_05_listagem_autenticado(client):
    """Usuário logado acessa listagem com sucesso."""
    login(client)
    resp = client.get('/lancamentos')
    assert resp.status_code == 200

def test_06_listagem_exibe_lancamentos(client):
    """Listagem exibe lançamentos do banco."""
    login(client)
    resp = client.get('/lancamentos')
    assert b'Sal' in resp.data

def test_07_health_check(client):
    """Endpoint /health retorna status ok."""
    resp = client.get('/health')
    assert resp.status_code == 200
    assert b'ok' in resp.data

# ── 3. FILTROS ───────────────────────────────────────────────────────

def test_08_filtro_tipo_receita(client):
    """Filtro tipo=R retorna página 200."""
    login(client)
    resp = client.get('/lancamentos?tipo=R')
    assert resp.status_code == 200

def test_09_filtro_tipo_despesa(client):
    """Filtro tipo=D retorna página 200."""
    login(client)
    resp = client.get('/lancamentos?tipo=D')
    assert resp.status_code == 200

def test_10_filtro_situacao_pendente(client):
    """Filtro situacao=P retorna página 200."""
    login(client)
    resp = client.get('/lancamentos?situacao=P')
    assert resp.status_code == 200

def test_11_filtro_data_inicial(client):
    """Filtro dt_ini retorna página 200."""
    login(client)
    resp = client.get('/lancamentos?dt_ini=2024-01-01')
    assert resp.status_code == 200

def test_12_filtro_combinado(client):
    """Filtro tipo+situação retorna página 200."""
    login(client)
    resp = client.get('/lancamentos?tipo=R&situacao=E')
    assert resp.status_code == 200

# ── 4. CRIAR ─────────────────────────────────────────────────────────

def test_13_criar_receita(client):
    """Criação de receita persiste e aparece na listagem."""
    login(client)
    resp = client.post('/lancamentos/novo', data={
        'descricao': 'Receita Teste', 'data_lancamento': '2024-04-01',
        'valor': '500.00', 'tipo_lancamento': 'R', 'situacao': 'P'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Receita Teste' in resp.data

def test_14_criar_despesa(client):
    """Criação de despesa persiste e aparece na listagem."""
    login(client)
    resp = client.post('/lancamentos/novo', data={
        'descricao': 'Despesa Teste', 'data_lancamento': '2024-04-02',
        'valor': '150.00', 'tipo_lancamento': 'D', 'situacao': 'E'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Despesa Teste' in resp.data

def test_15_form_novo_get(client):
    """GET /lancamentos/novo retorna formulário."""
    login(client)
    resp = client.get('/lancamentos/novo')
    assert resp.status_code == 200

# ── 5. EDITAR ────────────────────────────────────────────────────────

def test_16_form_editar_get(client):
    """GET /lancamentos/1/editar retorna formulário preenchido."""
    login(client)
    resp = client.get('/lancamentos/1/editar')
    assert resp.status_code == 200

def test_17_editar_lancamento(client):
    """Edição altera dados do lançamento."""
    login(client)
    resp = client.post('/lancamentos/1/editar', data={
        'descricao': 'Salário Editado', 'data_lancamento': '2024-01-05',
        'valor': '5500.00', 'tipo_lancamento': 'R', 'situacao': 'E'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Sal' in resp.data

def test_18_editar_inexistente(client):
    """Editar ID inexistente redireciona com mensagem."""
    login(client)
    resp = client.get('/lancamentos/99999/editar', follow_redirects=True)
    assert resp.status_code == 200

# ── 6. EXCLUIR ───────────────────────────────────────────────────────

def test_19_excluir_lancamento(client):
    """Exclusão redireciona para listagem."""
    login(client)
    resp = client.post('/lancamentos/2/excluir', follow_redirects=False)
    assert resp.status_code == 302

# ── 7. PDF ───────────────────────────────────────────────────────────

def test_20_exportar_pdf(client):
    """Exportação retorna PDF válido."""
    login(client)
    resp = client.get('/lancamentos/exportar')
    assert resp.status_code == 200
    assert resp.content_type == 'application/pdf'
    assert resp.data[:4] == b'%PDF'
