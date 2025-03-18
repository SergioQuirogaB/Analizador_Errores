from flask import Flask, render_template, request, send_file
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class LogAnalyzer:
    def __init__(self):
        self.errors = []
        self.process_errors = []
        self.processes = {}
        self.error_stats = {
            'critical': 0,
            'error': 0,
            'warning': 0,
            'timeout': 0,
            'connection': 0,
            'memory': 0,
            'database': 0,
            'security': 0
        }

    def analyze_file(self, file_path):
        try:
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        lines = file.readlines()
                        current_process = None
                        process_stack = []
                        
                        for line_num, line in enumerate(lines, 1):
                            timestamp = self._extract_timestamp(line)
                            
                            # Error detection
                            error_info = self._check_for_errors(line, line_num)
                            if error_info:
                                self.errors.append(error_info)
                                if current_process and current_process in self.processes:
                                    self.processes[current_process]['errors'].append(error_info)
                            
                            if self._is_process_start(line):
                                process_name = self._extract_process_name(line)
                                if process_name:
                                    current_process = process_name
                                    process_stack.append(process_name)
                                    self.processes[process_name] = {
                                        'start_line': line_num,
                                        'start_content': line.strip(),
                                        'start_time': timestamp,
                                        'end_line': None,
                                        'end_content': None,
                                        'end_time': None,
                                        'status': 'Corriendo ...',
                                        'duration': None,
                                        'errors': [],
                                        'parent_process': process_stack[-2] if len(process_stack) > 1 else None,
                                        'process_lines': [line.strip()],
                                        'all_content': []
                                    }

                            # Almacenar todas las líneas del proceso actual
                            if current_process and current_process in self.processes:
                                self.processes[current_process]['all_content'].append({
                                    'line_num': line_num,
                                    'content': line.strip(),
                                    'timestamp': timestamp
                                })

                            if self._is_process_end(line):
                                process_name = self._extract_process_name(line)
                                if process_name and process_name in self.processes:
                                    if process_stack and process_stack[-1] == process_name:
                                        process_stack.pop()
                                    
                                    self.processes[process_name].update({
                                        'end_line': line_num,
                                        'end_content': line.strip(),
                                        'end_time': timestamp,
                                        'status': 'Completado'
                                    })
                                    
                                    self.processes[process_name]['process_lines'].append(line.strip())
                                    
                                    if timestamp and self.processes[process_name]['start_time']:
                                        try:
                                            start = datetime.strptime(self.processes[process_name]['start_time'], '%Y-%m-%d %H:%M:%S')
                                            end = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                                            duration = (end - start).total_seconds()
                                            self.processes[process_name]['duration'] = duration
                                            self.processes[process_name]['duration_formatted'] = self._format_duration(duration)
                                        except ValueError:
                                            pass
                                    
                                    current_process = process_stack[-1] if process_stack else None

                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise UnicodeDecodeError("No se pudo decodificar el archivo")

        except Exception as e:
            self.process_errors.append(str(e))

    def _format_duration(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def _is_process_start(self, line):
        start_patterns = [
            r'(?i)iniciando proceso',
            r'(?i)inicio.*proceso',
            r'(?i)comenzando proceso',
            r'(?i)starting process',
            r'(?i)begin process',
            r'(?i)proceso iniciado',
            r'(?i)iniciando tarea',
            r'(?i)\[start\]',
            r'(?i)\[inicio\]',
            r'(?i)DEBUG.*iniciando',
            r'(?i)INFO.*iniciando',
            r'(?i)proceso reentrante',
            r'(?i)inicio de ejecución',
            r'(?i)comenzando ejecución'
        ]
        return any(re.search(pattern, line) for pattern in start_patterns)

    def _is_process_end(self, line):
        end_patterns = [
            r'(?i)finalizando proceso',
            r'(?i)fin.*proceso',
            r'(?i)proceso finalizado',
            r'(?i)terminando proceso',
            r'(?i)ending process',
            r'(?i)process completed',
            r'(?i)proceso completado',
            r'(?i)tarea finalizada',
            r'(?i)\[end\]',
            r'(?i)\[fin\]',
            r'(?i)DEBUG.*finalizado',
            r'(?i)INFO.*finalizado',
            r'(?i)fin de ejecución',
            r'(?i)ejecución completada'
        ]
        return any(re.search(pattern, line) for pattern in end_patterns)

    def _extract_process_name(self, line):
        patterns = [
            r'proceso (?:reentrante|para|de)?\s+(\w+)',
            r'proceso[:\s]+(\w+)',
            r'process[:\s]+(\w+)',
            r'\[([\w-]+)\]',
            r'tarea[:\s]+(\w+)',
            r'task[:\s]+(\w+)',
            r'DEBUG\s+(\w+)',
            r'INFO\s+(\w+)',
            r'iniciando\s+(\w+)',
            r'finalizando\s+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Si no encuentra un patrón específico, busca palabras después de ciertos indicadores
        words = line.split()
        for i, word in enumerate(words):
            if word.lower() in ['proceso', 'process', 'tarea', 'task', 'iniciando', 'finalizando']:
                if i + 1 < len(words):
                    return words[i + 1]
        return None

    def _extract_timestamp(self, line):
        patterns = [
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
            r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',
            r'\w{3} \d{2} \d{2}:\d{2}:\d{2} \d{4}',
            r'\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                try:
                    return datetime.strptime(match.group(), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
        return None

    def _check_for_errors(self, line, line_num):
        error_patterns = {
            'critical': [r'critical', r'fatal', r'urgente', r'grave'],
            'error': [r'error', r'exception', r'failed', r'failure', r'fallo', r'error occurred'],
            'warning': [r'warning', r'advertencia', r'precaución'],
            'timeout': [r'timeout', r'timed out', r'tiempo agotado'],
            'connection': [r'connection refused', r'connection failed', r'network error', r'conexión fallida'],
            'memory': [r'out of memory', r'memory exceeded', r'memoria insuficiente'],
            'database': [r'database error', r'db error', r'sql error', r'error de base de datos'],
            'security': [r'security violation', r'unauthorized', r'access denied', r'acceso denegado']
        }

        line_lower = line.lower()
        for error_type, patterns in error_patterns.items():
            if any(re.search(pattern, line_lower) for pattern in patterns):
                self.error_stats[error_type] += 1
                return {
                    'line': line_num,
                    'type': error_type,
                    'content': line.strip(),
                    'description': self._get_error_description(error_type, line),
                    'impact': self._get_error_impact(error_type),
                    'timestamp': self._extract_timestamp(line)
                }
        return None

    def _get_error_description(self, error_type, line):
        return f"{error_type.title()} detectado: {line.strip()}"

    def _get_error_impact(self, error_type):
        impacts = {
            'critical': "Fallo grave que requiere atención inmediata",
            'error': "Posible fallo en la ejecución del proceso",
            'warning': "Posible comportamiento inesperado",
            'timeout': "Posible bloqueo o sobrecarga del sistema",
            'connection': "Fallo en la comunicación con servicios externos",
            'memory': "Posible agotamiento de recursos del sistema",
            'database': "Problema con la base de datos",
            'security': "Posible brecha de seguridad"
        }
        return impacts.get(error_type, "Impacto desconocido")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'file' not in request.files:
        return render_template('index.html', error="No se seleccionó ningún archivo")
    
    file = request.files['file']
    if file.filename == '':
        return render_template('index.html', error="No se seleccionó ningún archivo")
    
    if not file.filename.endswith('.txt'):
        return render_template('index.html', error="Solo se permiten archivos .txt")
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    analyzer = LogAnalyzer()
    analyzer.analyze_file(filepath)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return render_template('results.html',
                         timestamp=timestamp,
                         errors=analyzer.errors,
                         process_errors=analyzer.process_errors,
                         processes=analyzer.processes,
                         error_stats=analyzer.error_stats)

if __name__ == '__main__':
    app.run(debug=True)