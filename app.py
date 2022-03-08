from flask import Flask, render_template, request, session, make_response, jsonify
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from recom import process_csv, get_cos_sim, recommend
import os

app = Flask(__name__)
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = "filesystem"
app.debug = True
Session(app)

BOOK_RECOM_ENV = os.environ.get("THREE_ONE_EIGHT_ENV")
if BOOK_RECOM_ENV == 'prod':
    app.debug = False
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("JAWSDB_URL")
else:
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/three_one_eight'

db = SQLAlchemy(app)

@app.before_first_request
def setup():
    db.create_all()
class User(db.model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = password

class App(db.model):
    __tablename__ = 'apps'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    first_item_id = db.Column(db.Integer)

    def __init__(self, name, user_id, first_item_id):
        self.name = name
        self.user_id = user_id
        self.first_item_id = first_item_id
        
class AppItem(db.model):
    __tablename__ = 'app_items'
    id = db.Column(db.Integer, primary_key=True)
    concat_data = db.Column(db.String(300), nullable=False)
    app_id = db.Column(db.Integer, db.ForeignKey('apps.id'))
    # cos_sim_row = db.Column(db.LargeBinary)
    
    def __init__(self, concat_data, app_id) -> None:
        self.concat_data = concat_data
        self.app_id = app_id

df = None
cos_sim = None

df = process_csv('./items20000.csv')
cos_sim = get_cos_sim(df)
indices = recommend('Red Queen 1', df, cos_sim)
print(df.iloc[indices])

###########################
########### API ###########
###########################
@app.route('/')
def home():
    return make_response('HOME', 200)

def custom_message(message, status_code): 
    return make_response(jsonify(message), status_code)

if __name__ == '__main__':
    app.run()
