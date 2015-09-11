from cgi import parse_qsl, FieldStorage
from wsgiref.simple_server import make_server
from tempfile import mkstemp
from random import randint
import os
import jinja2
from base64 import b64decode
import json
from time import time
import mimetypes
import shutil

# Code written by mandarine & f.reckl ! es
# Do whatever the hell you want with it

UP_DIR = '/var/www/freckles/uimgs/'
UP_NAME = 'image.jpg'
NUM_IMG = 1000
NUM_PER_DIR = 50
EXP_MIN = 2
EXP_MAX = 201
EXP_DEF = 13

TPL_PATH = '/var/www/freckles/templates'
DEFAULT_CTYPE = 'application/octet-stream'

EXTENSIONS = {"JPEG": (".jpg", "image/jpeg"),
              "PNG": (".png", "image/png"),
              "GIF": (".gif", "image/gif")}

def get_path(number, suffix = ".jpg"):
    subdir = int(int(number) / NUM_PER_DIR)
    new_number = number - (subdir * NUM_PER_DIR)
    subdir_path = os.path.join(UP_DIR, str(subdir))
    if not os.path.isdir(subdir_path):
        os.makedirs(subdir_path, 755)

    return os.path.join(subdir_path, str(new_number)+suffix)

def get_image(number):
    meta_path = get_path(number, ".json")
    ctype = 'image/jpeg'
    extension = '.jpg'
    countdown = 10
    metadata = {}
    try:
        with open(meta_path, 'r') as meta_file:
            metadata = json.load(meta_file)
            if 'type' in metadata:
                ctype = metadata['type'].encode()
            if 'ext' in metadata:
                extension = metadata['ext']
            if 'countdown' in metadata:
                countdown = metadata['countdown']
    except:
        pass

    temp_path = get_path(number, extension)
    try:
        with open(temp_path, 'r') as img_file:
            content = img_file.read()
    except:
        ctype = 'image/gif'
        img = "R0lGODlhAQABAIAAAP///////yH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="
        content = b64decode(img)
    else:
        countdown -= 1
        if countdown == 0:
            # Expire image
            os.remove(temp_path)
            os.remove(meta_path)
        else:
            metadata['countdown'] = countdown
            with open(meta_path, 'w') as meta_file:
                json.dump(metadata, meta_file)

    ret = "200 OK"
    return ret, ctype, content, []

def index():
    ret = '200 OK'
    ctype = 'text/html'
    tpl_loader = jinja2.FileSystemLoader( searchpath=TPL_PATH)
    tpl_env = jinja2.Environment( loader=tpl_loader )
    tpl = tpl_env.get_template('/uploader.html.j2')
    tpl_data = {'e_min': EXP_MIN, 'e_max': EXP_MAX, 'e_def': EXP_DEF}
    content = tpl.render(tpl_data).encode('utf-8')
    return ret, ctype, content, []

def redirect(url):
    ret = "302 Temporary Redirect"
    ctype = "text/plain"
    headers = [("Location", url)]
    content = ""
    return ret, ctype, content, headers

def application(environ, start_response):
    """Main WSGI entry point"""
    value = ""
    #query = unquote(environ['QUERY_STRING'])
    if environ['REQUEST_METHOD'] == 'GET':
        url = environ['PATH_INFO'].split('/')[1:]
        # /
        if len(url) == 1 and url[0] == '':
            ret, ctype, content, headers = index()
        # /<x>
        elif len(url) == 1 and url[0].isdigit() \
             and int(url[0]) <= NUM_IMG \
             and int(url[0]) > 0:
            img_id = int(url[0])
            ret, ctype, content, headers = get_image(img_id)
        else:
            ret, ctype, content, headers = redirect("/")

    elif environ['REQUEST_METHOD'] == 'POST':
        post_env = environ.copy()
        post_env['QUERY_STRING'] = ''
        fields = FieldStorage(fp=environ['wsgi.input'],environ=post_env, keep_blank_values=1)
        metadata = {}

        try:
            metadata['countdown'] = int(fields['countdown'].value)
            assert metadata['countdown'] >= EXP_MIN
            assert metadata['countdown'] <= EXP_MAX
        except:
            metadata['countdown'] = EXP_DEF

        fileitem = fields['file']
        _, image_file = mkstemp(suffix=os.path.basename(fileitem.filename))
        with open(image_file, 'wb') as upimage:
            upimage.write(fileitem.file.read())

        img_id = randint(1, NUM_IMG)
        ret, ctype, content, headers = redirect('/%s' % (img_id))

        try:
            _, img_extension = os.path.splitext(fileitem.filename)
            print "lol"
            print img_extension
            img_extension = img_extension.lower()
            metadata['ext'] = img_extension
            metadata['type'] = mimetypes.types_map.get(img_extension, DEFAULT_CTYPE)
            if metadata['type'] != DEFAULT_CTYPE:
                new_path = get_path(img_id, img_extension)
                shutil.copy(image_file, new_path)
                with open(get_path(img_id, ".json"), 'w') as meta_file:
                    json.dump(metadata, meta_file)
        except:
            raise

    start_response(ret, [('Content-Type', ctype)]+headers)
    return content

if __name__=='__main__':
    httpd = make_server('', 8080, application)
    print("Serving on port 8080...")
    httpd.serve_forever()
