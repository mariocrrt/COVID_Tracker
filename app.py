from flask import Flask, render_template, request
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import os
from flask_sqlalchemy import SQLAlchemy
from googletrans import Translator
translator = Translator()


#   LOADING AND ASSIGNING ENV FILES
load_dotenv()
API_KEY = os.getenv('API_KEY')
DB_URL = os.getenv('DB_URL')


result = requests.get('https://lab24.ilsole24ore.com/coronavirus/').text
soup = BeautifulSoup(result, 'lxml')


#   SCRAPING DATA
percentages = soup.findAll('span', class_="black")
cases_today_string = soup.find('h2', class_="timer count-number").text
date = soup.find('div', id="description").text


#   FORMATTING DATA FOR TELEGRAM BOT
percentage_today_string = percentages[6].text
percentage_last_week_string = percentages[7].text
date_today_string = date[:-50]

#   TELEGRAM MESSAGE
TELEGRAM_MESSAGE = f'{date_today_string}. \nNuovi casi: {cases_today_string}. \nTasso di positività di oggi: {percentage_today_string}. \nOggi una settimana fa: {percentage_last_week_string}.'


#   URLS
telegram_url = f'https://api.telegram.org/bot{API_KEY}/sendMessage?chat_id=@CovidInfoDaily&text={TELEGRAM_MESSAGE}'


#   FORMATTING DATA FOR API
API_PERCENTAGE_TODAY = float(
    percentage_today_string.split("%")[0].replace(',', '.'))

API_PERCENTAGE_LAST_WEEK = float(percentage_last_week_string.split("%")[
    0].replace(',', '.'))

API_CASES_TODAY = float(cases_today_string.split('+')[1])

API_DATE_TODAY_TEMP = date_today_string.replace(
    'Aggiornato al', '').replace('\n', '').strip()

out = translator.translate(API_DATE_TODAY_TEMP, dest='en')
API_DATE_TODAY = out.text


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL

#   INITIALIZING DB
db = SQLAlchemy(app)


#   CREATING DB MODEL
class covid_data(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cases_today = db.Column(db.Float, nullable=False)
    percentage_today = db.Column(db.Float, nullable=False)
    percentage_last_week = db.Column(db.Float, nullable=False)
    date = db.Column(db.String, nullable=False)

#   CREATE FUNCTION TO RETURN STRING WHEN ADDING TO DB
    def __repr__(self):
        return '<New Data Added (ID) %r>' % self.id


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        new_data = covid_data(percentage_today=API_PERCENTAGE_TODAY, percentage_last_week=API_PERCENTAGE_LAST_WEEK,
                              cases_today=API_CASES_TODAY, date=API_DATE_TODAY)

        try:
            db.session.add(new_data)
            db.session.commit()
            requests.get(telegram_url)

            return 'Data added to DB successfully.'
        except:
            return 'An error occurred while adding data...'

    else:
        data = covid_data.query.all()
        output = []
        for info in data:
            info_data = {'cases_today': info.cases_today, 'percentage_today': info.percentage_today,
                         'percentage_last_week': info.percentage_last_week, 'date': info.date}
            output.append(info_data)
        return {'data': output}


@app.route('/delete-cases/<id>', methods=['DELETE'])
def delete_cases(id):
    info = covid_data.query.get(id)
    if info is None:
        return {'error': 'not found'}
    db.session.delete(info)
    db.session.commit()
    return {'message': 'deleted.'}
