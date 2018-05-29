# nafsdm webinterface
# nafsdm_web.py
# main file for the flask engine behind the nafsdm webinterface
# (c) Vilhelm Prytz 2018
# https://github.com/mrkakisen/nafsdm

###########
## SETUP ##
###########

# imports
import logging
import sys
import subprocess
import os
import os.path
import platform
from versionCheck import *
from logPath import logPath
from database import *
from connAlive import *
from time import strftime

# flask setup
from flask import Flask
from flask import render_template, url_for, make_response, redirect, request, Response, flash
from functools import wraps

# import master version
import sys
sys.path.insert(0, "/home/master-nafsdm/pythondaemon")
from version import version as masterVersion


app = Flask(__name__)

# functions
def check_auth(username, password):
    f = open("/home/master-nafsdm/webinterface/interfacePassword.txt")
    passwordRaw = f.read()
    f.close()

    if len(passwordRaw.split("\n")) == 2:
        passReturn = passwordRaw.split("\n")[0]
    elif len(passwordRaw.split("\n")) == 1:
        passReturn = passwordRaw.split("\n")[0]
    else:
        return "Invalid password in configuration", 500

    return username == "admin" and password == passReturn

def authenticate():
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# for notifications sidebar
def prepNotifications():
    # all notifications
    notifications = []
    # down slaves
    downSlaves = listDownSlaves()
    for slave in downSlaves:
        notifications.append(["Node " + slave + " is currently offline!", "red"])

    # new update
    parseStatus, versionColor, versionMsg, github_branch, checkDate, isLatest = parseTempFiles()
    if parseStatus:
        if isLatest != True:
            notifications.append(["A new update is available!", "red"])

    # other notifications will also be added here

    return notifications

# for tmp files
def parseTempFiles():
    if os.path.isfile(".tmpVersionColor") and os.path.isfile(".tmpVersionMsg") and os.path.isfile(".tmpBranch") and os.path.isfile(".tmpDate") and os.path.isfile(".tmpIsLatest"):
        f = open(".tmpVersionColor")
        versionColor = f.read()
        f.close()

        f = open(".tmpVersionMsg")
        versionMsg = f.read()
        f.close()

        f = open(".tmpBranch")
        github_branch = f.read()
        f.close()

        f = open(".tmpDate")
        checkDate = f.read()
        f.close()

        f = open(".tmpIsLatest")
        isLatest = f.read()
        if "True" in isLatest:
            isLatest = True
        else:
            isLatest = False

        return True, versionColor, versionMsg, github_branch, checkDate, isLatest
    else:
        return False, None, None, None, None, None

# parse some .txt config files
def parseTxtConfig():
    github_branch = "master"
    devStatus = False
    devIcMode = False

    # dev function for specifing branch
    if os.path.isfile("/home/master-nafsdm/pythondaemon/dev_github_branch.txt"):
        f = open("/home/master-nafsdm/pythondaemon/dev_github_branch.txt")
        branchRaw = f.read()
        f.close()

        if "development" in branchRaw:
            github_branch = "development"

    # dev mode, disables auto updater
    if os.path.isfile("/home/master-nafsdm/pythondaemon/dev_devmode.txt"):
        f = open("/home/master-nafsdm/pythondaemon/dev_devmode.txt")
        devStatusRaw = f.read()
        f.close()
        if "True" in devStatusRaw:
            devStatus = True
        else:
            devStatus = False

    # dev ic mode
    if os.path.isfile("/home/master-nafsdm/pythondaemon/dev_ic_mode.txt"):
        f = open("/home/master-nafsdm/pythondaemon/dev_ic_mode.txt")
        devIcModeRaw = f.read()
        f.close()
        if "True" in devIcModeRaw:
            devIcMode = True
        else:
            devIcMode = False

    return github_branch, devStatus, devIcMode

# write new .txt config files
def writeTxtConfig(github_branch, devStatus, devIcMode):
    if github_branch == "master":
        if os.path.isfile("/home/master-nafsdm/pythondaemon/dev_github_branch.txt"):
            os.remove("/home/master-nafsdm/pythondaemon/dev_github_branch.txt")
    else:
        f = open("/home/master-nafsdm/pythondaemon/dev_github_branch.txt", "w")
        f.write(github_branch)
        f.close()

    if devStatus == "True":
        f = open("/home/master-nafsdm/pythondaemon/dev_devmode.txt", "w")
        f.write("True")
        f.close()
    else:
        if os.path.isfile("/home/master-nafsdm/pythondaemon/dev_devmode.txt"):
            os.remove("/home/master-nafsdm/pythondaemon/dev_devmode.txt")

    if devIcMode == "True":
        f = open("/home/master-nafsdm/pythondaemon/dev_ic_mode.txt", "w")
        f.write("True")
        f.close()
    else:
        if os.path.isfile("/home/master-nafsdm/pythondaemon/dev_ic_mode.txt"):
            os.remove("/home/master-nafsdm/pythondaemon/dev_ic_mode.txt")

    return True

# setup logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# format for logger
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# add stdout to logger
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)

# add file handler to logger
fh = logging.FileHandler(logPath)
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

logging.info("Welcome to nafsdm-master webinterface!")

####################
## ERROR HANDLERS ##
####################
@app.errorhandler(404)
def error_404(e):
    date = strftime("%Y-%m-%d %H:%M:%S")
    return render_template("errors/404.html", version=masterVersion, date=date), 404

@app.errorhandler(500)
def error_500(e):
    date = strftime("%Y-%m-%d %H:%M:%S")
    return render_template("errors/500.html", version=masterVersion, date=date), 500

@app.errorhandler(400)
def error_400(e):
    date = strftime("%Y-%m-%d %H:%M:%S")
    return render_template("errors/400.html", version=masterVersion, date=date), 400

#################
## MAIN ROUTES ##
#################
@app.route("/")
@requires_auth
def index():
    updateCheck = request.args.get("updateCheck")
    if updateCheck:
        status, devIcMode, github_branch, myVersion, newestVersion = checkUpdate()
        if status:
            if devIcMode:
                if myVersion == newestVersion:
                    versionColor = "green"
                    versionMsg = "Running latest incremental commits update - version " + myVersion

                    f = open(".tmpIsLatest", "w")
                    f.write("True")
                    f.close()
                else:
                    versionColor = "red"
                    versionMsg = "Not running latest incremental commits update (latest version is " + newestVersion + ")"

                    f = open(".tmpIsLatest", "w")
                    f.write("False")
                    f.close()
            else:
                if myVersion == newestVersion:
                    versionColor = "green"
                    versionMsg = "Running latest version - version " + myVersion

                    f = open(".tmpIsLatest", "w")
                    f.write("True")
                    f.close()
                else:
                    versionColor = "red"
                    versionMsg = "Not running latest version (latest version is " + newestVersion + ")"

                    f = open(".tmpIsLatest", "w")
                    f.write("False")
                    f.close()
        else:
            versionColor = "red"
            versionMsg = "Unable to establish connection to GitHub (connection issues?)"

            f = open(".tmpIsLatest", "w")
            f.write("True")
            f.close()

        f = open(".tmpVersionColor", "w")
        f.write(versionColor)
        f.close()

        f = open(".tmpVersionMsg", "w")
        f.write(versionMsg)
        f.close()

        f = open(".tmpBranch", "w")
        f.write(github_branch)
        f.close()

        f = open(".tmpDate", "w")
        f.write(strftime("%Y-%m-%d %H:%M:%S"))
        f.close()

        return redirect("/")

    # loadavg
    try:
        loadAvg = str(os.getloadavg()[0:4]).split("(")[1].split(")")[0]
    except Exception:
        loadAvg = "error"

    # get kernel version
    try:
        kernel = platform.platform()
    except Exception:
        kernel = "error"

    # Statistics
    try:
        domainsNumber = str(getStatistics()).split("(")[1].split(",")[0]
    except Exception:
        domainsNumber = "error"

    try:
        slavesNumber = str(len(slaveConnections()))
    except Exception:
        slavesNumber = "error"

    # notifications
    notifications = prepNotifications()

    parseStatus, versionColor, versionMsg, github_branch, checkDate, isLatest = parseTempFiles()

    date = strftime("%Y-%m-%d %H:%M:%S")
    return render_template("index.html", notifications=notifications, version=masterVersion, date=date, github_branch=github_branch, versionColor=versionColor, versionMsg=versionMsg, loadAvg=loadAvg, kernel=kernel, domainsNumber=domainsNumber, slavesNumber=slavesNumber, updateCheck=updateCheck, parseStatus=parseStatus, checkDate=checkDate)

@app.route("/domains")
@requires_auth
def domains():
    # get args
    remove = request.args.get("remove")
    add = request.args.get("add")
    addSuccess = request.args.get("addSuccess")
    removeSuccess = request.args.get("removeSuccess")
    fail = request.args.get("fail")
    editRaw = request.args.get("edit")
    editSuccess = request.args.get("editSuccess")

    try:
        edit = int(editRaw.split()[0])
    except Exception:
        edit = None

    domains = []
    domainsRaw = listDomains()
    for domain in domainsRaw:
        if domain[5] == "y":
            oneDomain = [domain[0], domain[1], domain[2], domain[3], domain[4], "Enabled", "y"]
        elif domain[5] == "n":
            oneDomain = [domain[0], domain[1], domain[2], domain[3], domain[4], "Disabled", "n"]
        else:
            oneDomain = [domain[0], domain[1], domain[2], domain[3], domain[4], domain[5], domain[5]]
        domains.append(oneDomain)

    # notifications
    notifications = prepNotifications()

    date = strftime("%Y-%m-%d %H:%M:%S")
    return render_template("domains.html", notifications=notifications, domains=domains, add=add, remove=remove, edit=edit, addSuccess=addSuccess, removeSuccess=removeSuccess, editSuccess=editSuccess, fail=fail, version=masterVersion, date=date)

@app.route("/slavestatus")
@requires_auth
def slavestatus():
    flushSuccess = request.args.get("flushSuccess")
    fail = request.args.get("fail")

    date = strftime("%Y-%m-%d %H:%M:%S")

    # notifications
    notifications = prepNotifications()

    slaves = slaveConnections()
    return render_template("slavestatus.html", notifications=notifications, slaves=slaves, flushSuccess=flushSuccess, fail=fail, version=masterVersion, date=date)

@app.route("/settings")
@requires_auth
def settings():
    success = request.args.get("success")
    fail = request.args.get("fail")

    date = strftime("%Y-%m-%d %H:%M:%S")

    # notifications
    notifications = prepNotifications()

    # get current status of all files
    github_branch, devStatus, devIcMode = parseTxtConfig()

    # get two values of the True/False values
    if devStatus:
        devStatusOpp = False
    else:
        devStatusOpp = True

    if devIcMode:
        devIcModeOpp = False
    else:
        devIcModeOpp = True

    if "master" in github_branch:
        github_branch = "master"
        github_branchOpp = "development"
    elif "development" in github_branch:
        github_branch = "development"
        github_branchOpp = "master"
    else:
        github_branchOpp = "error"

    return render_template("settings.html", notifications=notifications, version=masterVersion, date=date, github_branch=github_branch, github_branchOpp=github_branchOpp, devStatus=devStatus, devStatusOpp=devStatusOpp, devIcMode = devIcMode, devIcModeOpp=devIcModeOpp, success=success, fail=fail)

@app.route("/logviewer")
@requires_auth
def logviewer():
    date = strftime("%Y-%m-%d %H:%M:%S")

    # notifications
    notifications = prepNotifications()

    slaves = slaveConnections()
    return render_template("logviewer.html", notifications=notifications, version=masterVersion, date=date)

################
## API ROUTES ##
################
@app.route("/api/newDomain", methods=["POST"])
@requires_auth
def api_newDomain():
    domain = request.form["domain"]
    masterIP = request.form["masterIP"]
    comment = request.form["comment"]
    assignedNodes = request.form["assignedNodes"]
    dnssec = request.form["dnssec"]

    addDomain(domain, masterIP, comment, assignedNodes, dnssec)

    return redirect("/domains?addSuccess=true")

@app.route("/api/removeDomain")
@requires_auth
def api_removeDomain():
    domainId = request.args.get("id")

    status = removeDomain(domainId)

    if status == True:
        return redirect("/domains?removeSuccess=true")
    else:
        return redirect("/domains?fail=true")

@app.route("/api/editDomain", methods=["POST"])
@requires_auth
def api_editDomain():
    domainId = request.form["id"]
    domain = request.form["domain"]
    masterIP = request.form["masterIP"]
    comment = request.form["comment"]
    assignedNodes = request.form["assignedNodes"]
    dnssec = request.form["dnssec"]

    status = editDomain(domainId, domain, masterIP, comment, assignedNodes, dnssec)

    if status == True:
        return redirect("/domains?editSuccess=true")
    else:
        return redirect("/domains?fail=true")

@app.route("/api/slaveFlush")
@requires_auth
def api_slaveFlush():
    if not flushSlaveConnections():
        return redirect("/slavestatus?flushSuccess=true")
    else:
        return redirect("/slavestatus?fail=true")

@app.route("/api/settingsUpdate", methods=["POST"])
@requires_auth
def api_settingsUpdate():
    github_branch = request.form["github_branch"]
    devIcMode = request.form["devIcMode"]
    devStatus = request.form["devStatus"]

    if writeTxtConfig(github_branch, devStatus, devIcMode):
        return redirect("/settings?success=true")
    else:
        return redirect("/settings?fail=true")

@app.route("/api/logviewer")
@requires_auth
def api_logviewer():
     f = open("/home/master-nafsdm/webinterface_log.log")
     log = f.read()
     f.close()

     return "<pre>" + log + "</pre>"
