from flask import Flask, jsonify, request, render_template, send_file
import csv
import io
import sqlite3
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')
DB_NAME = 'vendas.db'


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto TEXT NOT NULL,
                preco REAL NOT NULL,
                data TEXT NOT NULL,
                status TEXT NOT NULL,
                origem TEXT NOT NULL,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        conn.commit()


def validate_venda(data):
    required = ['produto', 'preco', 'data', 'status', 'origem']
    for key in required:
        if key not in data or data[key] in (None, ''):
            raise ValueError(f'O campo "{key}" é obrigatório.')

    try:
        float(data['preco'])
    except (TypeError, ValueError):
        raise ValueError('O preço deve ser um número válido.')

    try:
        datetime.strptime(str(data['data']), '%Y-%m-%d')
    except ValueError:
        raise ValueError('A data deve estar no formato YYYY-MM-DD.')

    if str(data['status']).strip() == '':
        raise ValueError('O status não pode ficar vazio.')

    if str(data['origem']).strip() == '':
        raise ValueError('A origem não pode ficar vazia.')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/vendas', methods=['GET'])
def listar_vendas():
    query = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    origem = request.args.get('origem', '').strip()
    data_inicio = request.args.get('data_inicio', '').strip()
    data_fim = request.args.get('data_fim', '').strip()

    sql = 'SELECT * FROM vendas WHERE 1=1'
    params = []

    if query:
        sql += ' AND (produto LIKE ? OR origem LIKE ? OR status LIKE ?)'
        like = f'%{query}%'
        params.extend([like, like, like])

    if status:
        sql += ' AND status = ?'
        params.append(status)

    if origem:
        sql += ' AND origem = ?'
        params.append(origem)

    if data_inicio:
        sql += ' AND data >= ?'
        params.append(data_inicio)

    if data_fim:
        sql += ' AND data <= ?'
        params.append(data_fim)

    sql += ' ORDER BY data DESC, id DESC'

    conn = get_db_connection()
    rows = conn.execute(sql, params).fetchall()
    vendas = [dict(row) for row in rows]
    conn.close()
    return jsonify(vendas)


@app.route('/api/vendas', methods=['POST'])
def criar_venda():
    payload = request.get_json(silent=True) or {}
    try:
        validate_venda(payload)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    produto = str(payload['produto']).strip()
    preco = float(payload['preco'])
    data_venda = str(payload['data'])
    status = str(payload['status']).strip()
    origem = str(payload['origem']).strip()

    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO vendas (produto, preco, data, status, origem) VALUES (?, ?, ?, ?, ?)',
        (produto, preco, data_venda, status, origem)
    )
    conn.commit()
    venda_id = cursor.lastrowid
    conn.close()

    return jsonify({
        'id': venda_id,
        'produto': produto,
        'preco': preco,
        'data': data_venda,
        'status': status,
        'origem': origem
    }), 201


@app.route('/api/vendas/<int:id>', methods=['PUT'])
def atualizar_venda(id):
    payload = request.get_json(silent=True) or {}
    try:
        validate_venda(payload)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    conn = get_db_connection()
    row = conn.execute('SELECT id FROM vendas WHERE id = ?', (id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({'error': 'Venda não encontrada.'}), 404

    conn.execute(
        'UPDATE vendas SET produto = ?, preco = ?, data = ?, status = ?, origem = ? WHERE id = ?',
        (
            str(payload['produto']).strip(),
            float(payload['preco']),
            str(payload['data']),
            str(payload['status']).strip(),
            str(payload['origem']).strip(),
            id,
        )
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Venda atualizada com sucesso.'})


@app.route('/api/vendas/<int:id>', methods=['DELETE'])
def excluir_venda(id):
    conn = get_db_connection()
    row = conn.execute('SELECT id FROM vendas WHERE id = ?', (id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({'error': 'Venda não encontrada.'}), 404

    conn.execute('DELETE FROM vendas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Venda removida com sucesso.'})


@app.route('/api/relatorio')
def relatorio():
    conn = get_db_connection()

    total_geral = conn.execute(
        'SELECT COUNT(*) AS total_vendas, COALESCE(SUM(preco), 0) AS valor_total FROM vendas'
    ).fetchone()

    por_status = conn.execute(
        'SELECT status, COUNT(*) AS total, COALESCE(SUM(preco), 0) AS valor FROM vendas GROUP BY status ORDER BY total DESC'
    ).fetchall()

    por_origem = conn.execute(
        'SELECT origem, COUNT(*) AS total, COALESCE(SUM(preco), 0) AS valor FROM vendas GROUP BY origem ORDER BY valor DESC'
    ).fetchall()

    conn.close()

    return jsonify({
        'total_vendas': total_geral['total_vendas'],
        'valor_total': float(total_geral['valor_total'] or 0),
        'status': [dict(row) for row in por_status],
        'origem': [dict(row) for row in por_origem],
    })


@app.route('/api/export/csv')
def export_csv():
    conn = get_db_connection()
    rows = conn.execute('SELECT id, produto, preco, data, status, origem FROM vendas ORDER BY data DESC, id DESC').fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'produto', 'preco', 'data', 'status', 'origem'])

    for row in rows:
        writer.writerow([row['id'], row['produto'], row['preco'], row['data'], row['status'], row['origem']])

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='vendas.csv'
    )


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
