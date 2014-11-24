import requests
import json
import hashlib
from flask import Flask, redirect, render_template, request, url_for
app = Flask(__name__)

f = open('auth.json')
auth = json.loads(f.read())
KEY = auth['key']
SECRET = auth['secret']
f.close()
f = open('users.json')
USERS = json.loads(f.read())
f.close()


@app.route("/")
def index():
    url = 'https://trello.com/1/authorize?key=%s&name=TrelloVoter&response_type=token&scope=read,write' % KEY
    return render_template('index.html', url=url)


@app.route("/boards/")
def boards():
    url = 'https://trello.com/1/members/me?key=%s&token=%s' % (KEY, request.args['token'])
    response = requests.get(url)
    boards_ids = json.loads(response.text)['idBoards']
    boards = []
    for board_id in boards_ids:
        url = 'https://api.trello.com/1/board/%s?key=%s&token=%s' % (board_id, KEY, request.args['token'])
        response = requests.get(url)
        boards.append(json.loads(response.text))
    return json.dumps(boards)


@app.route("/lists/")
def lists():
    url = 'https://trello.com/1/boards/%s/lists?key=%s&token=%s' % (request.args['board_id'], KEY, request.args['token'])
    response = requests.get(url)
    return response.text


def save_users():
    f = open('users.json', 'w')
    f.write(json.dumps(USERS))
    f.close()    


@app.route("/update/<user_id>/")
def update(user_id):
    url = 'https://trello.com/1/lists/%s/cards?key=%s&token=%s' % (USERS[user_id]['list_id'], KEY, USERS[user_id]['token'])
    USERS[user_id]['cards'] = json.loads(requests.get(url).text)
    save_users()
    return redirect(url_for('vote', user_id=user_id))


@app.route("/create/", methods=["POST"])
def create():
    if request.method == 'POST':
        user_id = hashlib.sha256('random%05d' % len(USERS)).hexdigest()
        print user_id
        print request.form
        url = 'https://trello.com/1/lists/%s/cards?key=%s&token=%s' % (request.form['list'], KEY, request.form['token'])
        print url
        cards = json.loads(requests.get(url).text)
        USERS[user_id] = {
            'token': request.form['token'],
            'board_id': request.form['board'],
            'list_id': request.form['list'],
            'cards': cards}
        save_users()
        return redirect(url_for('vote', user_id=user_id))


@app.route("/vote/<user_id>/", methods=["GET", "POST"])
def vote(user_id):
    showall = (request.args.get('showall', '') == 'true')
    cards = USERS[user_id]['cards']
    if request.method == 'POST':
        ids = request.form['ids']
        print request.form
        if 'submitted_votes' in USERS[user_id]:
            USERS[user_id]['submitted_votes'].append(ids)
        else:
            USERS[user_id]['submitted_votes'] = [ids]
        for card in cards:
            if card['id'] in ids:
                card['idMembersVoted'].append(len(USERS[user_id]['submitted_votes']))
        save_users()
        return redirect(url_for('vote', user_id=user_id))
    for card in cards:
        card['hashtags'] = [label['name'].replace(' ', '_').lower() for label in card['labels']]
        card['votes'] = len(card['idMembersVoted']) if showall else 0
    cards = sorted(cards, key=lambda x: -x['votes'])
    return render_template(
        'voting.html',
        cards=cards,
        user_id=user_id,
        votes=sum([card['votes'] for card in cards]),
        showall=showall)


if __name__ == "__main__":
    app.run(debug=True)
