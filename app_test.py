import os
import tempfile
import unittest
from app import app, db, File, run_capture
from flask_uploads import ALL


class TestApp(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['UPLOADED_FILES_DEST'] = tempfile.mkdtemp()
        app.config['TSHARK_PATH'] = 'D:/programs/Wireshark/tshark.exe'
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        os.unlink(app.config['UPLOADED_FILES_DEST'])

    def test_upload_file(self):
        data = {'file': (open('test.pcap', 'rb'), 'test.pcap')}
        response = self.app.post('/upload', content_type='multipart/form-data', data=data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(File.query.all()), 1)

    def test_browse_files(self):
        file = File(name='test.pcap', path='test.pcap', file_type='application/vnd.tcpdump.pcap')
        db.session.add(file)
        db.session.commit()
        response = self.app.get('/browse?type=application/vnd.tcpdump.pcap')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'test.pcap', response.data)

    def test_view_file(self):
        file = File(name='test.pcap', path='test.pcap', file_type='application/vnd.tcpdump.pcap')
        db.session.add(file)
        db.session.commit()
        with app.app_context():
            run_capture('test.pcap')
            file = File.query.filter_by(name='test.pcap').first()
            self.assertIsNotNone(file.packets)


if __name__ == '__main__':
    unittest.main()
