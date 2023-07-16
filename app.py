import os
from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm
from flask_uploads import UploadSet, configure_uploads, ALL
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
import pyshark

# for tshark path
import platform
import configparser

config = configparser.ConfigParser()
config.read('app.config')

# Get the current platform
current_platform = platform.system()

# Retrieve the corresponding value based on the platform
tshark_path = config.get(current_platform, 'TSHARK_PATH')


from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

import threading
import asyncio

import json
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///files.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOADED_FILES_DEST'] = 'uploads'
# app.config['TSHARK_PATH'] = 'D:/programs/Wireshark/tshark.exe'

db = SQLAlchemy(app)

files = UploadSet('files', ALL)
configure_uploads(app, files)

# # Assume that packets is a list of dictionaries with timestamp keys as datetime objects
# packets = [{'protocol': 'ARP', 'source': '10.69.97.124', 'destination': '10.69.97.124', 'timestamp': datetime.now()}]

# Convert datetime objects to string representations
# for packet in packets:
#     packet['timestamp'] = packet['timestamp'].isoformat()

# Serialize to JSON
# json_data = json.dumps({'packets': packets})

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    path = db.Column(db.String(255))
    file_type = db.Column(db.String(50))
    packets = db.Column(db.JSON)

    def __repr__(self):
        return f"<File {self.id}>"


class FileForm(FlaskForm):
    file = files
    file_type = StringField('File type', validators=[DataRequired()])
    submit = SubmitField('Upload')


@app.route('/')
def home():
    return render_template('home.html')

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

def run_capture(file_name):
    print("I am inside run_capture method")
    asyncio.set_event_loop(asyncio.new_event_loop())
    print(f'filepath={file_name}')
    file_path = os.path.join(app.config['UPLOADED_FILES_DEST'], file_name)
    custom_tshark_path = app.config['TSHARK_PATH']
    with app.app_context():
        capture = pyshark.FileCapture(file_path, tshark_path=custom_tshark_path)
        # packets = [{'protocol': 'ARP', 'source': '10.69.97.124', 'destination': '10.69.97.124', 'timestamp': datetime.now()}]
        packets = []
        for packet in capture:

            packet_dict = {'protocol': packet.highest_layer, 'timestamp': packet.sniff_time.isoformat()}

            if packet.highest_layer == 'ARP':
                packet_dict['source'] = packet.arp.src_proto_ipv4
                packet_dict['destination'] = packet.arp.dst_proto_ipv4

            elif packet.highest_layer == 'IP':
                packet_dict['source'] = packet.ip.src
                packet_dict['destination'] = packet.ip.dst

            elif packet.highest_layer == 'IPv6':
                packet_dict['source'] = packet.ipv6.src
                packet_dict['destination'] = packet.ipv6.dst

            elif packet.highest_layer == 'TCP':
                packet_dict['source'] = f"{packet.ip.src}:{packet.tcp.srcport}"
                packet_dict['destination'] = f"{packet.ip.dst}:{packet.tcp.dstport}"

            elif packet.highest_layer == 'UDP':
                packet_dict['source'] = f"{packet.ip.src}:{packet.udp.srcport}"
                packet_dict['destination'] = f"{packet.ip.dst}:{packet.udp.dstport}"

            packets.append(packet_dict)

        capture.close()
        print("capture is closed")
        file = File.query.filter_by(path=file_name).first()
        json_data = json.dumps({'packets': packets})
        file.packets = json_data
        print("file packets are found")
        db.session.commit()
        print("I did commit to db session")
        print(f"Number of packets extracted: {len(packets)}")

        return


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
        thread.join() # wait for running the run_capture method

        # Fetch the File object from the database again to get the updated packets
        file = File.query.filter_by(path=file.path).first()

        if hasattr(file, 'packets'):
            return render_template('view_pcap.html', file=file, packets=file.packets)
        else:
            return
    else:
        return render_template('view_file.html', file=file)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
