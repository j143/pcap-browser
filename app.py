import os
from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm
from flask_uploads import UploadSet, configure_uploads, ALL
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
import pyshark

from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

import threading
import asyncio

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///files.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOADED_FILES_DEST'] = 'uploads'

db = SQLAlchemy(app)

files = UploadSet('files', ALL)
configure_uploads(app, files)


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    path = db.Column(db.String(255))
    file_type = db.Column(db.String(50))


class FileForm(FlaskForm):
    file = files
    file_type = StringField('File type', validators=[DataRequired()])
    submit = SubmitField('Upload')


@app.route('/')
def home():
    return render_template('home.html')


# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if 'file' not in request.files:
#         return "No file uploaded"
#
#     file = request.files['file']
#     if file.filename == '':
#         return "No file selected"
#
#     # save the file
#     filename = secure_filename(app.config.filename)
#     # file.save(filename)
#     file.save(filename)
#
#     return "File uploaded successfully"

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'file' in request.files:
        filename = files.save(request.files['file'])
        file = File(name=request.files['file'].filename, path=filename, file_type=request.files['file'].content_type)
        db.session.add(file)
        db.session.commit()
        return redirect(url_for('browse'))
    return render_template('upload.html')


@app.route('/browse', methods=['GET', 'POST'])
def browse(files=None):
    form = FileForm()
    print('here_iam in the first app.route')
    if form.validate_on_submit():
        filename = files.save(request.files['file'])
        file_type = form.file_type.data.lower()
        file = File(name=filename, path=files.path(filename), file_type=file_type)
        db.session.add(file)
        db.session.commit()
        return redirect(url_for('browse'))
    file_type = request.args.get('type', '').lower()
    if file_type:
        files = File.query.filter_by(file_type=file_type).all()
    else:
        files = File.query.all()
    return render_template('browse.html', files=files, form=form, file_type=file_type)


@app.route('/browse/<int:file_id>')
def view_file(file_id):
    # id = request.args.get('file_id')
    print(f"id={file_id}")
    file = File.query.get_or_404(file_id)
    if 1:
        # if file.file_type == 'application/vnd.tcpdump.pcap':
        # Extract packet details from pcap file
        thread = threading.Thread(target=run_capture, args=(file.path,))
        thread.start()

        return render_template('view_pcap.html', file=file)
    else:
        return render_template('view_file.html', file=file)


def run_capture(file_path):
    print("I am inside run_capture method")
    asyncio.set_event_loop(asyncio.new_event_loop())
    capture = pyshark.FileCapture(file_path)
    packets = []
    for packet in capture:
        print(f'packets: {packet.highest_layer}')
        packets.append({
            'protocol': packet.highest_layer,
            'source': packet.ip.src,
            'destination': packet.ip.dst,
            'timestamp': packet.sniff_time
        })
    capture.close()
    file = File.query.filter_by(path=file_path).first()
    file.packets = packets
    db.session.commit()


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
