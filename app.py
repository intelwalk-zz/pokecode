from hashlib import new
from io import StringIO
import mimetypes
from flask import Flask, render_template, request, make_response, Response
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
import requests
import csv
import json
import xml.etree.cElementTree as ET
from json2xml import json2xml
from json2xml.utils import readfromstring

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:intelwalk@localhost:5432/pokebase"
db = SQLAlchemy(app)
migrate = Migrate(app,db)

class KantoModel(db.Model):
    __tablename__ = 'kanto'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    capture_rate = db.Column(db.Integer())
    shape = db.Column(db.String())
    sprite = db.Column(db.String())


    children = relationship("KantoTypesModel")

    def __init__(self, id, name, capture_rate, shape,sprite):
        self.id = id
        self.name = name
        self.capture_rate = capture_rate
        self.shape = shape
        self.sprite = sprite

    def __repr__(self):
        return f"<Pokemon {self.name}>"

class KantoTypesModel(db.Model):
    __tablename__ = 'kantotypes'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String())

    parent_id = db.Column(db.Integer, ForeignKey('kanto.id'))

    def __init__(self, type,parent_id):
        self.type = type
        self.parent_id = parent_id

    def __repr__(self):
        return f"<Type {self.type}>"

def loaddata():
    # pokelink = 'https://pokeapi.co/api/v2/pokemon?limit=151'
    # r = requests.get(pokelink)
    # data = r.json()
    # d = data['results']     
    # result_dict = dict((i[i],i["name"],i["url"]) for i in d)
    # print(result_dict)
    #pokedict = {id:0, 'name': 'placeholder','capture_rate':45,'types':{},'shape':'shape'}
    #print(pokedict)
    pokelink = 'https://pokeapi.co/api/v2/pokemon-species/'
    pokelink2 = 'https://pokeapi.co/api/v2/pokemon/'
    for i in range(152):
        if(i == 0):
            continue

        url = pokelink + str(i)
        url2 = pokelink2 +str(i)
        r = requests.get(url)
        data = r.json()
       
        r2 = requests.get(url2)
        data2 = r2.json()
        
        id = data['id']
        name = data['name']
        capture_rate = data['capture_rate']
        shape = data['shape']['name']
        sprite = data2['sprites']['front_default']
        insert_pokemon(id, name, capture_rate, shape,sprite)
        temptypes = data2['types']
        for type in temptypes:
            new_type =type['type']['name']
            insert_types(i,new_type)


def insert_pokemon(id, name, capture_rate, shape,sprite):
    new_pokemon = KantoModel(id=id, name=name, capture_rate=capture_rate, shape=shape,sprite=sprite)
    db.session.add(new_pokemon)
    db.session.commit()

def insert_types(parent_id, type):
    new_type = KantoTypesModel(parent_id=parent_id, type=type)
    db.session.add(new_type)
    db.session.commit()


#loaddata()

@app.route('/', methods=['GET'])
def index():
    pokemons = KantoModel.query.all()
    results = [
        {
            "name":pokemon.name,
            "id":pokemon.id,
            "capture_rate":pokemon.capture_rate,
            "shape":pokemon.shape,
            "sprite":pokemon.sprite
    } for pokemon in pokemons]
    return render_template('index.html', results=results)

@app.route('/search', methods=['POST'])
def search():
    search = request.form.get('search')
    newsearch = "%{}%".format(search)
      
    pokemons = KantoModel.query.filter(KantoModel.name.like(newsearch.lower()))
    results = [
        {
            "name":pokemon.name,
            "id":pokemon.id,
            "capture_rate":pokemon.capture_rate,
            "shape":pokemon.shape,
            "sprite":pokemon.sprite
    } for pokemon in pokemons]
    return render_template('index.html', results=results)

@app.route('/showdetails/<id>', methods=['GET'])
def showdetails(id):
    pokemon = KantoModel.query.get(id)
    print(pokemon)
    poketypes = KantoTypesModel.query.filter(KantoTypesModel.parent_id == id)
    results = [
        {
            "name":pokemon.name,
            "id":pokemon.id,
            "capture_rate":pokemon.capture_rate,
            "shape":pokemon.shape,
            "sprite":pokemon.sprite
        }
    ]
    print(results)
    typeresults = [
        {
            "type":poketype.type
        }for poketype in poketypes
    ]
    print(typeresults)
    return render_template('showdetails.html', results=results, typeresults=typeresults)

@app.route('/export', methods=['POST'])
def export():
    type = request.form.get('type')
    id = request.form.get('id')
    pokemon = KantoModel.query.get(id)
    poketypes = KantoTypesModel.query.filter(KantoTypesModel.parent_id == id)
    typeholder = [
        {
            "type":"none"
        },
        {
            "type":"none"
        }
    ]
    typeresults = [
        {
            "type":poketype.type
        }for poketype in poketypes
    ]
    for i in range(len(typeresults)):
        typeholder[i]['type'] = typeresults[i]['type']

  
    fields = ['Pokedex #','Name','Capture Rate','Shape', 'Sprite', 'Type1','Type2']
    rows = [
        pokemon.id,
        pokemon.name,
        pokemon.capture_rate,
        pokemon.shape,
        pokemon.sprite,
        typeholder[0]['type'],
        typeholder[1]['type']
        ]
    if(type == 'csv'):
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(fields)
        cw.writerow(rows)
        response = make_response(si.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=export.csv'
        response.headers["Content-type"] = "text/csv"
        return response
    if(type == 'json'):
        results = [
        {
            "name":pokemon.name,
            "id":pokemon.id,
            "capture_rate":pokemon.capture_rate,
            "shape":pokemon.shape,
            "sprite":pokemon.sprite,
            "type1":typeholder[0]['type'],
            "type2":typeholder[1]['type']
        }
        ]
        data = json.dumps(results, indent=4)
        response = make_response(data)
        response.headers['Content-Disposition'] = 'attachment; filename=export.json'
        response.headers["Content-type"] = "text/json"
        return response
    if(type == 'xml'):
        firsttype = typeholder[0]['type']
        secondtype = typeholder[1]['type']
        results = {
            "name":pokemon.name,
            "id":pokemon.id,
            "capture_rate":pokemon.capture_rate,
            "shape":pokemon.shape,
            "sprite":pokemon.sprite,
            "type1":firsttype,
            "type2":secondtype
        }
        data = json.dumps(results, indent=4)
        xml = readfromstring(data)
        print(xml)

        response = make_response(json2xml.Json2xml(xml, wrapper="all", pretty=True).to_xml())
        response.headers['Content-Disposition'] = 'attachment; filename=export.xml'
        response.headers["Content-type"] = "application/xml"
        return response
        
if __name__ == '__main__':
    
    app.run(debug=True)

