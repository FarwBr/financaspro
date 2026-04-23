import os
import io
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

import psycopg2
import psycopg2.extras
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, make_response)
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'financas_secret_key_2024')

# ─── DATABASE ────────────────────────────────────────────────────────
DB_CONFIG = {
    'host':     os.environ.get('DB_HOST',     'localhost'),
    'port':     os.environ.get('DB_PORT',     '5432'),
    'dbname':   os.environ.get('DB_NAME',     'financas'),
    'user':     os.environ.get('DB_USER',     'financas'),
    'password': os.environ.get('DB_PASSWORD', 'financas123'),
}

def get_db():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn

# ─── EMAIL (Mailtrap) ────────────────────────────────────────────────
MAIL_CONFIG = {
    'host':     os.environ.get('MAIL_HOST',     'sandbox.smtp.mailtrap.io'),
    'port':     int(os.environ.get('MAIL_PORT', '587')),
    'user':     os.environ.get('MAIL_USER',     'SEU_USER_MAILTRAP'),
    'password': os.environ.get('MAIL_PASSWORD', 'SUA_SENHA_MAILTRAP'),
    'from':     os.environ.get('MAIL_FROM',     'financaspro@app.com'),
}

def send_email(subject, body, to='admin@financaspro.com'):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = MAIL_CONFIG['from']
        msg['To']      = to
        msg.attach(MIMEText(body, 'html'))
        with smtplib.SMTP(MAIL_CONFIG['host'], MAIL_CONFIG['port']) as s:
            s.starttls()
            s.login(MAIL_CONFIG['user'], MAIL_CONFIG['password'])
            s.sendmail(MAIL_CONFIG['from'], to, msg.as_string())
        return True
    except Exception as e:
        print(f'[Email] Erro: {e}')
        return False

def email_lancamento(lancamento, acao='criado'):
    tipo  = 'Receita' if lancamento['tipo_lancamento'] == 'R' else 'Despesa'
    color = '#00C896'  if lancamento['tipo_lancamento'] == 'R' else '#FF5C5C'
    body  = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;
                border:1px solid #eee;border-radius:8px;overflow:hidden">
      <div style="background:#111;padding:16px 24px">
        <h2 style="color:#fff;margin:0">FinançasPro</h2>
      </div>
      <div style="padding:24px">
        <p>Lançamento <b>{acao}</b> com sucesso:</p>
        <table style="width:100%;border-collapse:collapse;font-size:14px">
          <tr><td style="padding:6px;color:#666">Descrição</td>
              <td><b>{lancamento['descricao']}</b></td></tr>
          <tr style="background:#f9f9f9">
              <td style="padding:6px;color:#666">Data</td>
              <td>{lancamento['data_lancamento']}</td></tr>
          <tr><td style="padding:6px;color:#666">Tipo</td>
              <td style="color:{color}"><b>{tipo}</b></td></tr>
          <tr style="background:#f9f9f9">
              <td style="padding:6px;color:#666">Valor</td>
              <td><b>R$ {lancamento['valor']:.2f}</b></td></tr>
        </table>
      </div>
    </div>"""
    send_email(f'Lançamento {acao} — FinançasPro', body)

# ─── PDF ─────────────────────────────────────────────────────────────
def gerar_pdf(lancamentos, total_r, total_d, saldo):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2*cm, leftMargin=2*cm,
                             topMargin=2*cm,  bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle('t', fontName='Helvetica-Bold', fontSize=14,
                              spaceAfter=4)
    sub_s   = ParagraphStyle('s', fontName='Helvetica', fontSize=9,
                              spaceAfter=12, textColor=colors.HexColor('#666'))
    story = [
        Paragraph('FinançasPro — Relatório de Lançamentos', title_s),
        Paragraph(f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}', sub_s),
    ]
    resumo = Table(
        [['Total Receitas',   'Total Despesas',   'Saldo'],
         [f'R$ {total_r:.2f}', f'R$ {total_d:.2f}', f'R$ {saldo:.2f}']],
        colWidths=[5.5*cm, 5.5*cm, 5.5*cm]
    )
    resumo.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,0), colors.HexColor('#222')),
        ('TEXTCOLOR',  (0,0),(-1,0), colors.white),
        ('FONTNAME',   (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0),(-1,-1), 9),
        ('ALIGN',      (0,0),(-1,-1), 'CENTER'),
        ('GRID',       (0,0),(-1,-1), 0.5, colors.HexColor('#ccc')),
        ('TOPPADDING', (0,0),(-1,-1), 6),
        ('BOTTOMPADDING', (0,0),(-1,-1), 6),
        ('TEXTCOLOR',  (0,1),(0,1), colors.HexColor('#00A87E')),
        ('TEXTCOLOR',  (1,1),(1,1), colors.HexColor('#CC0000')),
        ('FONTNAME',   (0,1),(-1,1), 'Helvetica-Bold'),
    ]))
    story += [resumo, Spacer(1, 14)]
    data = [['#', 'Descrição', 'Data', 'Tipo', 'Valor', 'Situação']]
    for l in lancamentos:
        tipo = 'Receita' if l['tipo_lancamento'] == 'R' else 'Despesa'
        sit  = {'P': 'Pendente', 'E': 'Efetivado', 'C': 'Cancelado'}.get(
                l['situacao'], l['situacao'])
        data.append([str(l['id']), l['descricao'],
                     str(l['data_lancamento']), tipo,
                     f"R$ {l['valor']:.2f}", sit])
    t = Table(data, colWidths=[1*cm, 5.5*cm, 2.5*cm, 2.2*cm, 2.5*cm, 2.8*cm])
    cmds = [
        ('BACKGROUND',    (0,0),(-1,0), colors.HexColor('#222')),
        ('TEXTCOLOR',     (0,0),(-1,0), colors.white),
        ('FONTNAME',      (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0,0),(-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#F5F5F5')]),
        ('GRID',          (0,0),(-1,-1), 0.5, colors.HexColor('#ddd')),
        ('ALIGN',         (0,0),(-1,-1), 'LEFT'),
        ('TOPPADDING',    (0,0),(-1,-1), 5),
        ('BOTTOMPADDING', (0,0),(-1,-1), 5),
        ('LEFTPADDING',   (0,0),(-1,-1), 6),
    ]
    for i, row in enumerate(data[1:], 1):
        c = colors.HexColor('#00A87E') if row[3] == 'Receita' else colors.HexColor('#CC0000')
        cmds += [('TEXTCOLOR',(3,i),(3,i),c), ('TEXTCOLOR',(4,i),(4,i),c)]
    t.setStyle(TableStyle(cmds))
    story.append(t)
    doc.build(story)
    buf.seek(0)
    return buf

# ─── AUTH ────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ─── ROTAS ───────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('lancamentos'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM usuario WHERE login=%s AND situacao='A'",
                    (request.form['login'],))
        user = cur.fetchone()
        cur.close(); conn.close()
        if user and check_password_hash(user['senha'], request.form['senha']):
            session['user_id']   = user['id']
            session['user_name'] = user['nome']
            return redirect(url_for('lancamentos'))
        flash('Login ou senha inválidos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

def _query_lancamentos(args):
    tipo   = args.get('tipo', '')
    sit    = args.get('situacao', '')
    dt_ini = args.get('dt_ini', '')
    dt_fim = args.get('dt_fim', '')
    q = "SELECT * FROM lancamento WHERE 1=1"
    p = []
    if tipo:   q += " AND tipo_lancamento=%s"; p.append(tipo)
    if sit:    q += " AND situacao=%s";        p.append(sit)
    if dt_ini: q += " AND data_lancamento>=%s"; p.append(dt_ini)
    if dt_fim: q += " AND data_lancamento<=%s"; p.append(dt_fim)
    q += " ORDER BY data_lancamento DESC"
    return q, p, tipo, sit, dt_ini, dt_fim

@app.route('/lancamentos')
@login_required
def lancamentos():
    q, p, tipo, sit, dt_ini, dt_fim = _query_lancamentos(request.args)
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(q, p)
    rows = cur.fetchall()
    cur.close(); conn.close()
    total_r = sum(r['valor'] for r in rows if r['tipo_lancamento'] == 'R')
    total_d = sum(r['valor'] for r in rows if r['tipo_lancamento'] == 'D')
    return render_template('lancamentos.html', lancamentos=rows,
                           total_receita=total_r, total_despesa=total_d,
                           saldo=total_r - total_d,
                           filtro_tipo=tipo, filtro_situacao=sit,
                           filtro_dt_ini=dt_ini, filtro_dt_fim=dt_fim)

@app.route('/lancamentos/exportar')
@login_required
def exportar_pdf():
    q, p, *_ = _query_lancamentos(request.args)
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(q, p)
    rows = cur.fetchall()
    cur.close(); conn.close()
    total_r = sum(r['valor'] for r in rows if r['tipo_lancamento'] == 'R')
    total_d = sum(r['valor'] for r in rows if r['tipo_lancamento'] == 'D')
    buf  = gerar_pdf(rows, total_r, total_d, total_r - total_d)
    resp = make_response(buf.read())
    resp.headers['Content-Type']        = 'application/pdf'
    resp.headers['Content-Disposition'] = 'attachment; filename=lancamentos.pdf'
    return resp

@app.route('/lancamentos/novo', methods=['GET', 'POST'])
@login_required
def novo_lancamento():
    if request.method == 'POST':
        conn = get_db()
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """INSERT INTO lancamento
               (descricao, data_lancamento, valor, tipo_lancamento, situacao)
               VALUES (%s,%s,%s,%s,%s) RETURNING *""",
            (request.form['descricao'], request.form['data_lancamento'],
             float(request.form['valor']), request.form['tipo_lancamento'],
             request.form['situacao']))
        lancamento = cur.fetchone()
        conn.commit(); cur.close(); conn.close()
        email_lancamento(lancamento, 'criado')
        flash('Lançamento criado com sucesso!', 'success')
        return redirect(url_for('lancamentos'))
    return render_template('form_lancamento.html', lancamento=None, acao='Novo')

@app.route('/lancamentos/<int:lid>/editar', methods=['GET', 'POST'])
@login_required
def editar_lancamento(lid):
    conn = get_db()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM lancamento WHERE id=%s", (lid,))
    lancamento = cur.fetchone()
    if not lancamento:
        cur.close(); conn.close()
        flash('Lançamento não encontrado.', 'danger')
        return redirect(url_for('lancamentos'))
    if request.method == 'POST':
        cur.execute(
            """UPDATE lancamento
               SET descricao=%s, data_lancamento=%s, valor=%s,
                   tipo_lancamento=%s, situacao=%s
               WHERE id=%s RETURNING *""",
            (request.form['descricao'], request.form['data_lancamento'],
             float(request.form['valor']), request.form['tipo_lancamento'],
             request.form['situacao'], lid))
        lancamento = cur.fetchone()
        conn.commit(); cur.close(); conn.close()
        email_lancamento(lancamento, 'atualizado')
        flash('Lançamento atualizado com sucesso!', 'success')
        return redirect(url_for('lancamentos'))
    cur.close(); conn.close()
    return render_template('form_lancamento.html', lancamento=lancamento, acao='Editar')

@app.route('/lancamentos/<int:lid>/excluir', methods=['POST'])
@login_required
def excluir_lancamento(lid):
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("DELETE FROM lancamento WHERE id=%s", (lid,))
    conn.commit(); cur.close(); conn.close()
    flash('Lançamento excluído.', 'success')
    return redirect(url_for('lancamentos'))

@app.route('/health')
def health():
    return {'status': 'ok', 'env': os.environ.get('APP_ENV', 'prod')}, 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
