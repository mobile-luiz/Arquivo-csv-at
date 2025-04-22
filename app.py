from flask import Flask, request, render_template, send_file, url_for
import PyPDF2
import pandas as pd
import io
import re
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = 'static'

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if not file or not file.filename.endswith('.pdf'):
        return render_template('index.html', error="Arquivo inválido. Envie um PDF válido.")

    try:
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded.pdf')
        file.save(file_path)
        pdf_url = url_for('static', filename='uploaded.pdf')

        pdf_reader = PyPDF2.PdfReader(file_path)
        text = ''
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + '\n'

        if not text.strip():
            return render_template('index.html', error="Nenhum texto extraído do PDF.", pdf_url=pdf_url)

        # Captura do nome da prefeitura
        linhas = text.strip().split('\n')
        nome_prefeitura = ''
        for linha in linhas[:10]:
            if "PREFEITURA" in linha.upper():
                nome_prefeitura = linha.strip()
                break
        if not nome_prefeitura:
            for linha in linhas[:10]:
                if "CNPJ" in linha.upper():
                    idx = linhas.index(linha)
                    if idx > 0:
                        nome_prefeitura = linhas[idx - 1].strip()
                    else:
                        nome_prefeitura = linha.strip()
                    break
        if not nome_prefeitura:
            nome_prefeitura = "Prefeitura não identificada"

        # Regex para dados
        pattern = re.compile(
            r'(?P<codigo>\d{1,2}(?:\.\d{1,2}){1,6})\s+(?P<descricao>.+?)\s{2,}(?P<previsto>[0-9.]+,[0-9]{2})\s+(?P<arrecadado>[0-9.]+,[0-9]{2})'
        )

        data = []
        for match in pattern.finditer(text):
            codigo = match.group('codigo')
            descricao = match.group('descricao').strip()
            previsto = match.group('previsto')
            arrecadado = match.group('arrecadado')
            data.append([codigo, descricao, previsto, arrecadado])

        if not data:
            return render_template('index.html', error="Não foi possível extrair os dados corretamente.", pdf_url=pdf_url, nome_prefeitura=nome_prefeitura)

        headers = ["Código", "Descrição da Rubrica", "Previsto", "Arrecadado até Mês"]
        df = pd.DataFrame(data, columns=headers)

        csv_output = io.StringIO()
        df.to_csv(csv_output, index=False, sep=';', encoding='utf-8')
        csv_string = csv_output.getvalue()

        return render_template('index.html', texto=text, csv_data=csv_string, pdf_url=pdf_url, nome_prefeitura=nome_prefeitura)

    except Exception as e:
        return render_template('index.html', error=f"Erro: {str(e)}")

@app.route('/download-csv', methods=['POST'])
def download_csv():
    csv_data = request.form['csv_data']
    output = io.BytesIO()
    output.write(u'\ufeff'.encode('utf-8'))
    output.write(csv_data.encode('utf-8'))
    output.seek(0)
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name='resultado.csv')

if __name__ == '__main__':
    app.run(debug=True)
