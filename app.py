import json

from flask import Flask, render_template, request, session, redirect, url_for, g, Response

from scorekeeper.const import JSON_RESPONSE_HEADERS, STATUS_201_CREATED, STATUS_417_EXPECTATION_FAILED, \
    STATUS_200_SUCCESS, STATUS_400_BAD_REQUEST
from scorekeeper.db import TeamsDB, EventsDB, BuzzerTrackerDB
from scorekeeper.forms import LoginForm

# TODO: Establishes connection the  Monogo Databases
team_db = TeamsDB("192.168.99.100:27017")
event_db = EventsDB("192.168.99.100:27017")
buzzer_db = BuzzerTrackerDB("192.168.99.100:27017")


def validate_user(uname, password):
    """
    This function provides User validation for the specified username and password.

    :param uname:
    :param password:
    :return: True if user is authenticated, else False.
    """
    if team_db.get_team_doc(uname):
        doc = team_db.get_team_doc(uname)
        if doc['passwd'] == password:
            return True

    return False


app = Flask(__name__)

# app.config['SECRET_KEY'] = os.urandom(24)
app.config['SECRET_KEY'] = "MY_KEY"


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()

    # Runs if Form is submitted and posted
    if login_form.validate_on_submit():
        form = request.form
        user = form['username']
        passwd = form['password']

        result = validate_user(user, passwd)
        # TODO: Runs if the User validation fails
        if result is False:
            return redirect(url_for('login'))

        session['username'] = user

        return redirect(url_for('home', username=user, token=session['csrf_token']))

    return render_template('login.j2', form=login_form)


@app.route('/home')
def home():
    # TODO: Extracts the session and team object from the request.

    team_doc = team_db.get_team_doc(session['username'])
    sorted_docs = team_db.get_teams_positions()

    new_docs = []
    for indx, doc in enumerate(sorted_docs):
        doc['index'] = indx + 1
        new_docs.append(doc)

    return render_template("index.j2", team_data=team_doc, sorted_docs=new_docs)


@app.route('/')
def index():
    if session.get("username"):
        if session['username'] == "ringmaster":
            return redirect(url_for("ringmaster"))

    if g.user:
        return redirect(url_for("home"))

    return redirect(url_for('login'))


@app.route('/pcap1', methods=['GET', 'POST'])
def pcap1():
    event_data = event_db.get_event("PCAP1")

    event_responses = team_db.get_responses_by_event_id(session['username'], 'PCAP1')

    event_questions = event_db.get_event_questions("PCAP1")

    team_doc = team_db.get_team_doc(session['username'])

    return render_template("pcap1.j2", team_data=team_doc, questions=event_questions, event_data=event_data,
                           event_responses=event_responses)


@app.route('/pcap2', methods=['GET', 'POST'])
def pcap2():
    event_data = event_db.get_event("PCAP2")

    event_responses = team_db.get_responses_by_event_id(session['username'], 'PCAP2')
    event_questions = event_db.get_event_questions("PCAP2")

    team_doc = team_db.get_team_doc(session['username'])

    return render_template("pcap1.j2", team_data=team_doc, questions=event_questions, event_data=event_data,
                           event_responses=event_responses)


@app.route('/pcap3', methods=['GET', 'POST'])
def pcap3():
    event_data = event_db.get_event("PCAP3")
    event_responses = team_db.get_responses_by_event_id(session['username'], 'PCAP3')
    event_questions = event_db.get_event_questions("PCAP3")

    team_doc = team_db.get_team_doc(session['username'])

    return render_template("pcap1.j2", team_data=team_doc, questions=event_questions, event_data=event_data,
                           event_responses=event_responses)


@app.route("/opcyberjustice")
def opcyberjustice():
    event_data = event_db.get_event("OCJ")

    event_responses = team_db.get_responses_by_event_id(session['username'], 'OCJ')
    event_questions = event_db.get_event_questions("OCJ")

    team_doc = team_db.get_team_doc(session['username'])

    return render_template("pcap1.j2", team_data=team_doc, questions=event_questions, event_data=event_data,
                           event_responses=event_responses)


@app.route('/buzzer', methods=['GET', 'POST'])
def buzzer():
    event_data = event_db.get_event("PCAP3")
    event_responses = team_db.get_responses_by_event_id(session['username'], 'PCAP3')
    event_questions = event_db.get_event_questions("PCAP3")

    team_doc = team_db.get_team_doc(session['username'])

    return render_template("buzzer.j2", team_data=team_doc, questions=event_questions, event_data=event_data,
                           event_responses=event_responses)


@app.route('/ringmaster', methods=['GET'])
def ringmaster():
    team_doc = team_db.get_team_doc(session['username'])
    games_list = event_db.get_game_list()

    docs = team_db.get_all_docs()

    return render_template("ringmaster.j2", team_data=team_doc, games_list=games_list, team_docs=docs)


@app.before_request
def before_request():
    g.user = None
    if 'username' in session:
        g.user = session['username']


# Routes used for FrontEnd data calls
@app.route("/getteamscore", methods=['POST'])
def getteamscore():
    """
    Gets the current score for the specified team

    :return
    """
    data = request.json

    if isinstance(team_db.get_points(data.get('name')), int):
        points = team_db.get_points(data.get('name'))

        return Response(json.dumps({"name": data.get("name"), "points": points}),
                        status=STATUS_200_SUCCESS,
                        headers=JSON_RESPONSE_HEADERS)

    return Response(json.dumps({"name": data.get("name"), "msg": f"Error finding team"}),
                    status=STATUS_400_BAD_REQUEST,
                    headers=JSON_RESPONSE_HEADERS)


@app.route("/validate", methods=['POST'])
def validate():
    data = request.json
    response = data.get("response")
    name = data.get("name")
    q_id = data.get("q_id")
    event_id = data.get("event_id")

    if not team_db.get_team_doc(name):
        return Response(json.dumps({"result": False, "msg": "Invalid Team Name"}),
                        status=STATUS_400_BAD_REQUEST,
                        headers=JSON_RESPONSE_HEADERS)

    question = event_db.get_question(event_id, q_id)
    if question:
        if question.get("answer"):
            if question.get("answer") == response:

                cached_resp = team_db.get_response_by_event_id(name, event_id, q_id)

                if cached_resp:
                    if cached_resp['points_awarded']:
                        return Response(json.dumps({"result": True, "msg": "Points Already Awarded"}),
                                        status=STATUS_200_SUCCESS,
                                        headers=JSON_RESPONSE_HEADERS)

                team_obj = team_db.get_team_doc(name)

                new_response = {
                    "event_id": event_id,
                    "q_id": q_id,
                    "response": response,
                    "points_awarded": True
                }

                team_obj['responses'].append(new_response)
                team_obj['points'] += int(question['point_value'])
                team_db.update_data(name, team_obj)

                return Response(json.dumps({"result": True, "msg": "Correct"}),
                                status=STATUS_200_SUCCESS,
                                headers=JSON_RESPONSE_HEADERS)
            else:
                return Response(json.dumps({"result": False, "msg": "Incorrect"}),
                                status=STATUS_200_SUCCESS,
                                headers=JSON_RESPONSE_HEADERS)

    return Response(json.dumps({"result": False, "msg": "Event not Found"}),
                    status=STATUS_417_EXPECTATION_FAILED,
                    headers=JSON_RESPONSE_HEADERS)


@app.route('/dropsession')
def dropsession():
    """
    This endpoint drops the users active session.
    :return:
    """
    session.pop('username', None)
    return redirect(url_for("login"))


@app.route('/rest_response')
def rest_response():
    if team_db.reset_responses(session['username']):
        return Response

    return Response


@app.route('/reset_response', methods=['POST'])
def reset_response():
    """
    Resets the responses and clear the points for the provided name.

    :return:
    """
    data = request.json

    try:
        name = data['name']
        if team_db.reset_responses(name):
            return Response(json.dumps({"msg": f'User: "{name}" responses have been cleared', "result": True}),
                            status=STATUS_200_SUCCESS,
                            headers=JSON_RESPONSE_HEADERS)
        else:
            return Response(json.dumps({"msg": f'User: "{name}" not found', "result": False}),
                            status=STATUS_417_EXPECTATION_FAILED,
                            headers=JSON_RESPONSE_HEADERS)

    except Exception as err:
        return Response(json.dumps({"msg": f'ERROR: {str(err)}', "result": False}),
                        status=STATUS_400_BAD_REQUEST,
                        headers=JSON_RESPONSE_HEADERS)


@app.route('/team_buzzed', methods=['POST'])
def team_buzzed():
    """
    Creates buzzed record in the buzzer_tracker database. This function will timestamp each buzzed event.

    :return:
    """
    data = request.json

    try:

        team_name = data['team_name']
        user_resp = data['user_resp']

        resp_example = {
            "team_name": team_name,
            "response": user_resp,
            "time_stamp": 0.0,
            "time": "",
            "submitted": False
        }
        if not team_db.get_team_doc(team_name):
            return Response(json.dumps({"msg": f'not a valid team', "result": False}),
                            status=STATUS_400_BAD_REQUEST,
                            headers=JSON_RESPONSE_HEADERS)

        if buzzer_db.buzzed(resp_example):
            return Response(json.dumps({"msg": f'User: "{team_name}" has been created', "result": True}),
                            status=STATUS_201_CREATED,
                            headers=JSON_RESPONSE_HEADERS)
        else:
            return Response(json.dumps({"msg": f'Unable process buzz', "result": False}),
                            status=STATUS_417_EXPECTATION_FAILED,
                            headers=JSON_RESPONSE_HEADERS)

    except Exception as err:

        return Response(json.dumps({"msg": f'ERROR: {str(err)}', "result": False}),
                        status=STATUS_400_BAD_REQUEST,
                        headers=JSON_RESPONSE_HEADERS)


@app.route('/buzzed', methods=['POST'])
def buzzed():
    data = request.form
    team_name = session['username']
    user_resp = data['user_resp']

    resp_example = {
        "team_name": team_name,
        "response": user_resp,
        "time_stamp": 0.0,
        "time": "",
        "submitted": False
    }

    result = buzzer_db.buzzed(resp_example)

    return Response(json.dumps({"result": result}), status=200, headers=JSON_RESPONSE_HEADERS)


@app.route('/buzzer_clear', methods=['POST'])
def buzzer_clear():
    team_name = session['username']
    if buzzer_db.remove_response(team_name):
        return Response(json.dumps({"result": True}), status=200, headers=JSON_RESPONSE_HEADERS)

    return Response(json.dumps({"result": False}), status=200, headers=JSON_RESPONSE_HEADERS)


@app.route('/buzzer_load', methods=['POST'])
def buzzer_load():
    team_name = session['username']
    if buzzer_db.is_present(team_name):
        doc = buzzer_db.get_response(team_name)
        del doc['_id']
        print(doc)
        return Response(json.dumps({"doc": doc, "result": True}), status=200, headers=JSON_RESPONSE_HEADERS)

    return Response(json.dumps({"result": False, "doc": None}), status=200, headers=JSON_RESPONSE_HEADERS)


@app.route("/register", methods=['POST'])
def register():
    """
    Registers a new team to the database. Checks if the team is already present, will not over right if True.

    :return:
    """
    data = request.json

    name = data.get("name")
    passwd = data.get("passwd")
    if team_db.add_team(name, passwd):
        return Response(json.dumps({"msg": f'User: "{name}" has been created', "result": True}),
                        status=STATUS_201_CREATED,
                        headers=JSON_RESPONSE_HEADERS)

    else:
        return Response(json.dumps({"msg": "User Already Present in Database", "result": False}),
                        status=STATUS_417_EXPECTATION_FAILED,
                        headers=JSON_RESPONSE_HEADERS)


@app.route("/unregister", methods=['POST'])
def unregister():
    data = request.json
    name = data.get("name")
    if team_db.remove_team(name):
        return Response(json.dumps({"msg": f'User: "{name}" has been removed', "result": True}),
                        status=STATUS_200_SUCCESS,
                        headers=JSON_RESPONSE_HEADERS)

    return Response(json.dumps({"msg": "Nothing to remove", "result": False}), status=STATUS_417_EXPECTATION_FAILED,
                    headers=JSON_RESPONSE_HEADERS)


@app.route("/new_event", methods=['POST'])
def new_event():
    """
    Adds a new event to the database.

    :return:
    """
    data = request.json

    if event_db.add_event(doc=data):
        return Response(json.dumps({"msg": f'Event: "{data.get("event_id")}" has been created', "result": True}),
                        status=STATUS_201_CREATED,
                        headers=JSON_RESPONSE_HEADERS)
    else:
        return Response(json.dumps({"msg": f'Event: "{data.get("event_id")}" Already Exist', "result": False}),
                        status=417,
                        headers=STATUS_417_EXPECTATION_FAILED)


@app.route("/new_event_questions", methods=['POST'])
def new_event_questions():
    """
    Adds new questions to the supplied event ID.

    :return:
    """
    data = request.json

    if event_db.add_event_questions(data):
        return Response(json.dumps({"msg": f'Question for: "{data.get("event_id")}" has been added', "result": True}),
                        status=STATUS_201_CREATED,
                        headers=JSON_RESPONSE_HEADERS)

    return Response(json.dumps(
        {"msg": f'Unable to add question for: "{data.get("event_id")}", possible duplicate q_id in database',
         "result": False}), status=STATUS_417_EXPECTATION_FAILED,
        headers=JSON_RESPONSE_HEADERS)


@app.route("/remove_event_questions", methods=['POST'])
def remove_event_questions():
    """
    Removes a list of questions from an event.

    :return:
    """
    data = request.json

    if event_db.remove_event_questions(data):
        return Response(
            json.dumps({"msg": f'Questions for: "{data.get("event_id")}" has been removed', "result": True}),
            status=STATUS_200_SUCCESS,
            headers=JSON_RESPONSE_HEADERS)
    else:
        return Response(json.dumps({"msg": f'Error removing Questions for: "{data.get("event_id")}"', "result": False}),
                        status=STATUS_417_EXPECTATION_FAILED,
                        headers=JSON_RESPONSE_HEADERS)


@app.route("/remove_event", methods=['POST'])
def remove_event():
    """
    Removes an event from the database.

    :return:
    """
    data = request.json
    if event_db.remove_event(data.get("event_id")):
        return Response(json.dumps({"msg": f'Event: "{data.get("event_id")}" has been removed', "result": True}),
                        status=STATUS_200_SUCCESS,
                        headers=JSON_RESPONSE_HEADERS)
    else:
        return Response(json.dumps({"msg": f'Nothing to remove', "result": True}), status=STATUS_417_EXPECTATION_FAILED,
                        headers=JSON_RESPONSE_HEADERS)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
