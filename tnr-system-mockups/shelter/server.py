import http.server
import socketserver

Handler = http.server.SimpleHTTPRequestHandler
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(('', 8889), Handler) as httpd:
    print('Serving at port 8889')
    httpd.serve_forever()