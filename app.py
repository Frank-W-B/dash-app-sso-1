# Built with Python 3.13
# reset secret and Issuer URL

import os
from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
from identity.web import Auth
import dash
from dash import html, dcc
from werkzeug.middleware.proxy_fix import ProxyFix


# Initialize Flask and Session
app = Flask(__name__)
# Tells Flask to trust the incoming HTTPS header from the Azure proxy
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)
app.config["SESSION_TYPE"] = "filesystem"  # Stores data on server
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")
Session(app)


# Configure Entra ID Authentication using environment variables
# Initialize the Microsoft Identity Auth utility
auth = Auth(
    session=session,
    authority=f"https://login.microsoftonline.com/{os.environ.get('TENANT_ID')}",
    client_id=os.environ.get("CLIENT_ID"),
    client_credential=os.environ.get("CLIENT_SECRET")
)


# Flask Routes for Auth (Login, Authentication, Logout)
@app.route("/")
def index():
    return render_template('sign_on_page.html')


@app.route("/login")
def login():
    # Redirect user to Microsoft SSO login portal
    auth_url = auth.log_in(
        scopes=["User.Read"],
        redirect_uri=url_for("auth_response", _external=True)
    )
    return redirect(auth_url["auth_uri"])


@app.route("/getAToken")
def auth_response():
    # Process code/tokens returned by Microsoft identity provider
    result = auth.complete_log_in(request.args)
    #print(f'user: {auth.get_user()}')
    if "error" in result:
        return render_template("auth_error.html", result=result) 
        #return f"Authentication failed: {result.get('error_description')}", 400
    return redirect(url_for("/dashboard/")) # Redirect to Dash index after login


@app.route("/logout")
def logout():
    # Clear local session and get redirect URL to log out of Microsoft 
    logout_url = auth.log_out(url_for("index", _external=True))
    return redirect(logout_url)


# Security - redirect to index if there isn't an authenticated user 
@app.before_request
def restrict_access():
    if request.endpoint in ['index', 'login', 'auth_response']:
        return None
    if auth.get_user() is None:
        return redirect(url_for("index", _external=True))
    return None         

# ------------------ start dash app ----------------------------------------
# Initialize the Dash App, linking it to the Flask server
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/dashboard/')
dash_app.layout = html.Div([
    html.H1("Secure Dashboard"),
    html.P("Welcome to the authenticated portion of the application!"),
    dcc.Graph(
        id='example-graph',
        figure={
            'data': [{'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'Sales'}],
            'layout': {'title': 'Dash Data'}
        }
    ),
    html.A("Logout", href="/logout", style={"color": "red", "textDecoration": "none", "fontWeight": "bold"}),
])

# ------------------ end dash app ----------------------------------------

if __name__ == "__main__":
    app.run(host="localhost", port=3000, debug=True)


