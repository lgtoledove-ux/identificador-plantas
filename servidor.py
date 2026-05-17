"""
Servidor del identificador de plantas.
Funciona tanto en local como hospedado en Render/Replit/etc.

Uso local:
  python servidor.py
  Luego abre http://localhost:8000

En produccion (Render):
  Render asigna automaticamente el puerto via variable PORT.
"""

import http.server
import urllib.request
import urllib.error
import ssl
import os
import sys
import traceback
import json

# Render asigna el puerto via variable de entorno PORT
PORT = int(os.environ.get('PORT', 8000))
PLANTNET_API = 'https://my-api.plantnet.org/v2/identify/all'

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


class PlantNetProxyHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        # Si entran a la raiz, redirigir al identificador
        if self.path == '/' or self.path == '':
            self.send_response(302)
            self.send_header('Location', '/identificador-plantas.html')
            self.end_headers()
            return
        # Health check para Render
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'ok')
            return
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/identify'):
            self._proxy_to_plantnet()
        else:
            self.send_error(404, 'Not Found')

    def _proxy_to_plantnet(self):
        try:
            query = self.path.split('?', 1)[1] if '?' in self.path else ''
            url = f'{PLANTNET_API}?{query}' if query else PLANTNET_API

            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            content_type = self.headers.get('Content-Type', '')

            print(f'  -> POST {url[:80]}...')
            print(f'  -> Tamano del body: {content_length // 1024} KB')

            req = urllib.request.Request(url, data=body, method='POST')
            req.add_header('Content-Type', content_type)
            req.add_header('User-Agent', 'PlantIdentifier/1.0')

            with urllib.request.urlopen(req, timeout=120, context=SSL_CTX) as response:
                response_body = response.read()
                self.send_response(response.status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response_body)
                print(f'  <- OK ({len(response_body)} bytes)')

        except urllib.error.HTTPError as e:
            error_body = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_body)
            print(f'  <- Error HTTP {e.code}: {error_body[:200]}')

        except Exception as e:
            tb = traceback.format_exc()
            err_type = type(e).__name__
            err_msg = str(e) or '(sin mensaje)'
            print(f'  <- EXCEPCION: {err_type}: {err_msg}')
            print(tb)

            payload = json.dumps({
                'message': f'Server error: {err_type}: {err_msg}',
                'type': err_type
            })
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(payload.encode('utf-8'))

    def log_message(self, format, *args):
        sys.stderr.write(f'  {args[0]}\n')


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if script_dir:
        os.chdir(script_dir)

    # Bind a 0.0.0.0 para que funcione en Render (no solo localhost)
    server = http.server.HTTPServer(('0.0.0.0', PORT), PlantNetProxyHandler)
    print('=' * 64)
    print(f'  Servidor del identificador de plantas corriendo')
    print(f'  Puerto: {PORT}')
    print(f'  Local: http://localhost:{PORT}/')
    print('=' * 64)
    print('  Presiona Ctrl+C para detener (local)')
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido.')
        server.server_close()


if __name__ == '__main__':
    main()
