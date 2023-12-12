from flask import Flask, request, render_template
import subprocess

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        command = f'ping -c 3 {url}'
        try:
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, timeout=5)
            return render_template('index.html', url=url, response=output.decode())
        except subprocess.CalledProcessError as e:
            return render_template('index.html', url=url, response=e.output.decode())
        except subprocess.TimeoutExpired:
            return render_template('index.html', url=url, response='Command execution timed out.')
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)