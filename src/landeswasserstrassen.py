from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
import json
import datetime
import time
import os
from urllib.parse import urlparse, parse_qs
from azure.storage.blob import BlobClient
import base64
from apscheduler.schedulers.background import BackgroundScheduler


conn_str = os.environ.get('AZURE_CONN_STR')
# container_name = os.environ.get('AZURE_CONTAINER_NAME')
container_name = """$web"""
blob_name_export = os.environ.get('AZURE_BLOB_NAME_EXPORT')
blob_name_store = os.environ.get('AZURE_BLOB_NAME_STORE')
blob_export = BlobClient.from_connection_string(conn_str=conn_str, container_name=container_name, blob_name=blob_name_export)
blob_store = BlobClient.from_connection_string(conn_str=conn_str, container_name=container_name, blob_name=blob_name_store)

dir_path = os.path.dirname(os.path.realpath(__file__))

htaccess_user = os.environ.get('USER')
htaccess_pass = os.environ.get('PASSWORD')
user_pass = htaccess_user+':'+htaccess_pass
authorization_string = base64.b64encode(user_pass.encode('ascii')).decode('ascii')

HOST_NAME = os.environ.get('HOST')
PORT_NUMBER = int(os.environ.get('PORT'))

MESSAGE_TYPES = list(map(lambda s: s.split(':'), os.environ.get('MESSAGE_TYPES').split(';')))

FUTURE_LIMIT_DAYS = int(os.environ.get('FUTURE_LIMIT_DAYS'))

LOG_LEVEL = os.environ.get('LOG_LEVEL')
TRACE = 'TRACE'
DEBUG = 'DEBUG'
INFO = 'INFO'

sched = BackgroundScheduler()

def trace(message):
    if LOG_LEVEL==TRACE:
        print(message)
def debug(message):
    if LOG_LEVEL==DEBUG or LOG_LEVEL==TRACE:
        print(message)
def info(message):
    if LOG_LEVEL==INFO or LOG_LEVEL==DEBUG or LOG_LEVEL==TRACE:
        print(message)

class Server(BaseHTTPRequestHandler):
    def do_HEAD(self):
        trace("send header")
        self.send_response(200)
        content_type = 'text/html'
        if self.path.endswith('.css'):
            content_type = 'text/css'
        elif self.path.endswith('.js'):
            content_type = 'text/javascript'
        elif self.path.endswith('.svg'):
            content_type = 'image/svg+xml'
        self.send_header('Content-type', content_type)
        self.end_headers()

    def do_AUTHHEAD(self):
        trace("send header")
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"DPS Berlin\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self.handle_http()
        pass

    def do_POST(self):
        self.handle_http()
        pass

    def handle_http(self):
        ''' Present frontpage with user authentication. '''
        if self.headers['Authorization'] == None:
            self.do_AUTHHEAD()
            self.wfile.write('no auth header received'.encode())
            pass
        elif self.headers['Authorization'] == 'Basic '+authorization_string:
            if self.path.startswith('/edit'):
                params = parse_qs(urlparse(self.path).query)
                number = params.get('number', None)
                year = params.get('year', None)
                if number != None and year != None:
                    entry = self.findEntry(number[0], year[0])
                    self.wfile.write(self.getSite(self.getForm(False, entry, {})).encode())
                else:
                    self.wfile.write(self.getSite(self.getForm(True, {}, {})).encode())
            elif self.path.startswith('/js/') or self.path.startswith('/css/'):
                try:
                    f = open(dir_path + self.path, 'rb')
                    self.do_HEAD()
                    self.wfile.write(f.read())
                    f.close()
                except IOError:
                    self.send_error(404,'File Not Found: %s' % self.path)
            elif self.path.startswith('/create?'):
                (entry, messages) = self.saveEntry(True)
                if len(messages) > 0:
                    self.wfile.write(self.getSite(self.getForm(True, entry, messages)).encode())
                else:
                    self.forward_to_start()
            elif self.path.startswith('/update?'):
                (entry, messages) = self.saveEntry(False)
                if len(messages) > 0:
                    self.wfile.write(self.getSite(self.getForm(False, entry, messages)).encode())
                else:
                    self.forward_to_start()
            elif self.path.startswith('/delete?'):
                params = parse_qs(urlparse(self.path).query)
                number = params.get('number', None)[0]
                year = params.get('year', None)[0]
                self.deleteEntry(number, year)
                self.forward_to_start()
            else:
                self.wfile.write(self.getSite(self.getEntryList()).encode())
            pass
        else:
            self.do_AUTHHEAD()
            self.wfile.write('not authenticated'.encode())
            pass

    def forward_to_start(self):
        self.send_response(303)
        self.send_header('Location','./')
        self.end_headers()

    def findEntry(self, number, year):
        for feature in data['features']:
            if feature['properties']['number'] == number and feature['properties']['year'] == year:
                return feature

    def deleteEntry(self, number, year):
        for feature in data['features']:
            if feature['properties']['number'] == number and feature['properties']['year'] == year:
                data['features'].remove(feature)
        writeData()

    def getSite(self, content):
        self.do_HEAD()
        page = '<!DOCTYPE html>\n<html>\n'
        page += '<head>\n'
        page += '<title>Landeswasserstraßen Berlin</title>\n'
        page += '<meta charset="utf-8"/>\n'
        page += '<link href="./css/style.css" rel="stylesheet" type="text/css">'
        page += '<link href="./css/leaflet.css" rel="stylesheet" type="text/css">'
        page += '<link href="./css/leaflet.draw.css" rel="stylesheet" type="text/css">'
        page += '<link href="./css/flatpickr.min.css" rel="stylesheet" type="text/css">'
        page += '<script type="text/javascript" src="./js/jquery-3.2.1.min.js"></script>\n'
        page += '<script type="text/javascript" src="./js/leaflet.js"></script>\n'
        page += '<script type="text/javascript" src="./js/leaflet.draw.js"></script>\n'
        page += '<script type="text/javascript" src="./js/bootstrap.min.js"></script>\n'
        page += '<script type="text/javascript" src="./js/flatpickr.min.js"></script>\n'
        page += '<script type="text/javascript" src="./js/main.js"></script>\n'
        page += '</head>\n'
        page += '<body>\n'+content+'</body>\n'
        page += '</html>\n'
        return page

    def getForm(self, isNew, entry, messages):
        number = self.getProperty(entry, 'number', '')
        year = self.getProperty(entry, 'year', '')
        title = self.getProperty(entry, 'title', '')
        messageType = self.getProperty(entry, 'messageType', '').lower()
        waterway = self.getProperty(entry, 'waterway', '')
        description = self.getProperty(entry, 'description', '')
        valid = self.getProperty(entry, 'valid', None)
        valid_from = ''
        valid_to = ''
        if valid != None:
            if 'from' in valid and valid['from'] != None:
                valid_from = valid['from']
            if 'to' in valid and valid['to'] != None:
                valid_to = valid['to']
        spatial = self.getSpatialFromEntry(entry)

        action = './update'
        if isNew:
            action = './create'

        form = '<form action="'+action+'">\n'
        form += '<input type="hidden" id="number" name="number" value="'+number+'"/>\n'
        form += '<input type="hidden" id="year" name="year" value="'+year+'"/>\n'
        form += self.getTextField('title', 'Betreff', title, messages)
        form += '<div class="message-types">'
        for type in MESSAGE_TYPES:
            form += self.getRadioField(type[0], 'messageType', type[1], messageType)
        form += '</div>\n'
        if 'messageType' in messages:
            form += '<span class="message-text">'+messages['messageType']+'</span><br>\n'
        form += self.getTextField('waterway', 'Wasserstraße', waterway, messages)
        form += '<label for="description" class="form-label">Beschreibung:</label> <textarea  rows="10" cols="30" id="description" name="description">'+description+'</textarea><br/>\n'
        form += self.getTextField('valid-from', 'Gültig Von', valid_from, messages)
        form += self.getTextField('valid-to', 'Gültig Bis', valid_to, messages)
        # Verortung
        form += '<div id="map" style=""></div>\n'
        if 'spatial' in messages:
            form += '<span class="message-text">'+messages['spatial']+'</span><br>\n'
        form += '<input type="hidden" id="spatial" name="spatial" value="'+spatial+'"/><br/>\n'
        #Abschicken
        form += '<input type="submit" value="Speichern"/><button type="button" onclick="window.location.href=\'./\'">Abbrechen</button><br/>\n'
        form += '</form>\n'
        return form

    def getTextField(self, id, label, value, messages, readonly=False):
        css_class = ''
        if id in messages:
            css_class = ' class="have-message"'
        readonly_text = ''
        if readonly:
            readonly_text = ' readonly'
        message_snippet = '<span class="message-text">'+messages[id]+'</span>' if id in messages else ''
        result = '<label for="'+id+'" class="form-label">'+label+':</label> <input type="text" id="'+id+'" name="'+id+'" value="'+value+'"'+css_class+readonly_text+'/><br/>\n'
        if id in messages:
            result += '<span class="message-text">'+messages[id]+'</span><br>'
        return result


    def getRadioField(self, id, group, label, value):
        result = '<span class="radio-field-entry"><input type="radio" id="'+id+'" name="'+group+'" value="'+id+'"'
        if id == value:
            result += ' checked="checked"'
        result += '> <label for="'+id+'">'+label+'</label></span>\n'
        return result

    def getSpatialFromEntry(self, entry):
        if not entry is None and 'geometries' in entry and not entry['geometries'] is None:
            spatials = [];
            for geometry in entry['geometries']:
                if 'coordinates' in geometry:
                    spatials.append([geometry['coordinates']])
                elif 'geometries' in geometry:
                    spatials.append(geometry['geometries'][len(geometry['geometries'])-1]['coordinates'])
            return json.dumps(spatials, sort_keys=False)
        return ''

    def getProperty(self, entry, key, default):
        if 'properties' in entry:
            if key in entry['properties'] and not entry['properties'][key] is None:
                return entry['properties'][key]
        return default

    def getEntryList(self):
        result = '<table>\n'
        result += '<tr><th>Meldung</th><th>Titel</th><th>Gültig ab</th><th>Gültig bis</th><th>Aktionen</th></tr>\n'
        for feature in data['features']:
            css_class = ''
            if (not feature['properties']['valid']['to'] is None) and (datetime.datetime.strptime(feature['properties']['valid']['to'], "%Y-%m-%dT%H:%M") < datetime.datetime.now()):
                css_class = ' class="outdated"'
            valid_from = str(feature['properties']['valid']['from']) if not feature['properties']['valid']['from'] is None else '';
            valid_to = str(feature['properties']['valid']['to']) if not feature['properties']['valid']['to'] is None else '';
            result += '<tr>'
            result += '<td'+css_class+'>'+str(feature['properties']['number'])+'/'+str(feature['properties']['year'])+'</td>'
            result += '<td'+css_class+'>'+str(feature['properties']['title'])+'</td>'
            result += '<td'+css_class+'>'+valid_from+'</td>'
            result += '<td'+css_class+'>'+valid_to+'</td>'
            result += '<td'+css_class+'><a href="./edit?number='+str(feature['properties']['number'])+'&year='+str(feature['properties']['year'])+'">Bearbeiten</a>\n'
            result += '<a href="./delete?number='+str(feature['properties']['number'])+'&year='+str(feature['properties']['year'])+'">Löschen</a></td>\n'
            result += '</tr>\n'
        result += '</table>\n'
        result += '<a href=./edit>Neuen Eintrag anlegen</a>\n'
        return result


    def saveEntry(self, isNew):
        params = parse_qs(urlparse(self.path).query)

        number = self.getParam(params, 'number')
        year = self.getParam(params, 'year')
        title = self.getParam(params, 'title')
        waterway = self.getParam(params, 'waterway')
        messageType = self.getParam(params, 'messageType').upper() if not self.getParam(params, 'messageType') is None else None
        description = self.getParam(params, 'description')
        valid_from = self.getParam(params, 'valid-from')
        valid_to = self.getParam(params, 'valid-to')
        spatials = json.loads(self.getParam(params, 'spatial')) if not self.getParam(params, 'spatial') is None else None

        properties = {
            'number': number,
            'year': year,
            'title': title,
            'waterway': waterway,
            'messageType': messageType,
            'description': description,
            'valid': {
                'from': valid_from,
                'to': valid_to
            }
        }


        geometries = []
        if not spatials is None:
            for spatial in spatials:
                geometry = None
                type = 'Point'
                coordinates = spatial
                if(len(spatial) > 1):
                    geometry = {'type': 'GeometryCollection', 'geometries': []}
                    geometry['geometries'].append({'type': 'Point', 'coordinates': spatial[0]})
                    geometry['geometries'].append({'type': 'Point', 'coordinates': spatial[len(spatial)-1]})
                    geometry['geometries'].append({'type': 'LineString', 'coordinates': spatial})
                else:
                    geometry = {'type': 'Point', 'coordinates': spatial[0]}
                geometries.append(geometry)


        feature = {
            'type': 'Feature',
        }
        feature['properties'] = properties
        feature['geometries'] = geometries

        entry = self.findEntry(number, year)

        messages = {}
        #if isNew and not entry is None:
        #    messages['number'] = 'Eine Meldung ' + str(number)+'/'+str(year) + ' ist bereits vorhanden!'
        #if number is None:
        #    messages['number'] = 'Geben Sie eine Meldungsnummer an!'
        #if year is None:
        #    messages['year'] = 'Geben Sie ein Meldungsjahr an!'
        if title is None:
            messages['title'] = 'Geben Sie einen Titel an!'
        if messageType is None:
            messages['messageType'] = 'Geben Sie einen Typ für die Meldung an!'
        if waterway is None:
            messages['waterway'] = 'Geben Sie eine Wasserstraße an!'
        if valid_from is None:
            messages['valid-from'] = 'Geben Sie ein Startdatum an!'
        if spatials is None or len(spatials) == 0:
            messages['spatial'] = 'Geben Sie einen Raumbezug an!'

        if not len(messages) > 0:
            if isNew:
                data['properties']['lastNumber'] += 1
                currentYear = datetime.datetime.now().year
                lastYear = data['properties']['lastYear']
                if lastYear != currentYear:
                    data['properties']['lastNumber'] = 1
                    data['properties']['lastYear'] = currentYear
                number = data['properties']['lastNumber']
                feature['name'] = str(number)+'/'+str(currentYear)
                feature['properties']['number'] = str(number)
                feature['properties']['year'] = str(currentYear)
                data['features'].append(feature)
            else:
                print(json.dumps(entry, sort_keys=False))
                print(json.dumps(feature, sort_keys=False))
                entry['properties'] = feature['properties']
                entry['geometries'] = feature['geometries']

            writeData()

        return (feature, messages)

    def getParam(self, params, key):
        array = params.get(key, None)
        if array != None and len(array) > 0:
            return array[0]
        return None

data  = {'type':'FeatureCollection','features':[]}

@sched.scheduled_job('interval', hours=1)
def writeData():
    info('Write Data')
    with open("./landeswasserstrassen_full.json", encoding="utf-8", mode="w") as out_file:
        json.dump(data, indent=4, sort_keys=False, ensure_ascii=False, fp=out_file)
    with open("./landeswasserstrassen_full.json", mode="rb") as out_file:
        blob_store.upload_blob(out_file, overwrite=True)

    filtered = {'type':'FeatureCollection','features':[]}
    for feature in data['features']:
        if feature['properties']['valid']['to'] is None or datetime.datetime.strptime(feature['properties']['valid']['to'], "%Y-%m-%dT%H:%M") >= datetime.datetime.now():
            if datetime.datetime.strptime(feature['properties']['valid']['from'], "%Y-%m-%dT%H:%M") - datetime.timedelta(days=FUTURE_LIMIT_DAYS) <= datetime.datetime.now():
                for geometry in feature['geometries']:
                    copy = feature.copy()
                    copy['geometry'] = geometry
                    del copy['geometries']
                    filtered['features'].append(copy)

    with open("./landeswasserstrassen.json", encoding="utf-8", mode="w") as out_file:
        json.dump(filtered, indent=4, sort_keys=False, ensure_ascii=False, fp=out_file)
    with open("./landeswasserstrassen.json", mode="rb") as out_file:
        blob_export.upload_blob(out_file, overwrite=True)



def loadData():
    global data
    if blob_store.exists():
        info('load Data')
        download_stream = blob_store.download_blob()
        data = json.loads(download_stream.readall())
    else:
        info('Data not exists')

    if not 'properties' in data:
        data['properties'] = {}
    if not 'lastYear' in data['properties']:
        data['properties']['lastYear'] = datetime.datetime.now().year
    if not 'lastNumber' in data['properties']:
        data['properties']['lastNumber'] = 0

    if 'features' in data:
        for feature in data['features']:
            if 'geometry' in feature:
                feature['geometries'] = [feature['geometry']]
                del feature['geometry']

info('Started')
loadData()
sched.start()

if __name__ == '__main__':
    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), Server)
    print(time.asctime(), 'Server UP - %s:%s' % (HOST_NAME, PORT_NUMBER))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print(time.asctime(), 'Server DOWN - %s:%s' % (HOST_NAME, PORT_NUMBER))
