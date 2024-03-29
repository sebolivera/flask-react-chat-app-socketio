from click import option
from utils import get_email, get_user, isSafe, isEmail, allowed_file, isValidStr
from flask import Blueprint, send_from_directory, request, jsonify, current_app
from database import db_session
from flask_jwt_extended import create_access_token, get_jwt_identity, \
    unset_jwt_cookies, jwt_required, verify_jwt_in_request
from dotenv import load_dotenv
from models import *
from sqlalchemy import desc, or_, and_
import bcrypt
from datetime import datetime
import os
from werkzeug.utils import secure_filename
load_dotenv()
# I have zero explanation as to why I did it this way
TESTING = os.getenv('TESTING')
routes = Blueprint('example_blueprint', __name__)


@routes.route("/logout", methods=["GET"])
def logout():
    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    return response


@routes.route("/contactlist")
@jwt_required()
def list_contacts():
    try:
        s = db_session()
        # idk why I used one() instead of first(). Inconsistency aside, we'll say it's because I like using an alternative version for practice
        user = s.query(User).filter_by(email=get_email()).one()
        q = s.query(Friend).filter_by(userId=user.id).all()
        res = []
        for e in q:
            friend = s.query(User).get(e.friendId)
            res.append(
                friend.serialize)
        s.close()
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    return jsonify(res)


@routes.route("/check_room", methods=["POST"])
@jwt_required()
def check_room():
    q = None
    try:
        s = db_session()
        groupId = request.json.get("groupId", None)
        if not groupId:
            s.close()
            return {"error": "No group provided"}, 401
        q = s.query(Group).filter(
            Group.users.any(id=get_jwt_identity())).all()
        s.close()
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    if not q:
        return {"error": "User doesn't have access to this room"}, 401
    else:
        return {"success": "User has access to this room"}, 200


@routes.route('/register')
def register():
    return {'registred': True}


@routes.route('/profile')
@jwt_required()
def my_profile():  # to be completed later
    try:
        s = db_session()
        user = s.query(User).filter_by(email=get_email()).one()
        s.close()
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Session desynchronized"}, 401
    return jsonify(user.serialize)


@routes.route('/get_info', methods=["GET"])
@jwt_required()
def get_info():
    try:
        user = get_user(get_jwt_identity())
    except Exception as e:
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    if not user:
        return {"error": "User not found"}, 404
    response = jsonify(user.serialize)
    return response


@routes.route('/token', methods=["POST"])
def create_token():
    email = request.json.get("email", None)
    password = request.json.get("password", None)
    try:
        s = db_session()
        userTry = s.query(UserSalt).filter_by(email=email).first()
        if not userTry:
            return {"msg": "Wrong email"}, 401
        salt = userTry.salt
        user = s.query(User).filter_by(
            email=email, password=bcrypt.hashpw(password=str.encode(password, 'utf-8'), salt=salt)).first()
        if not user:
            return {"msg": "Wrong password"}, 401
        access_token = create_access_token(identity=user.id)
        notifications = user.get_notification_amount()
        response = {"access_token": access_token,
                    "firstName": user.firstName,
                    "lastName": user.lastName,
                    "email": user.email,
                    "notifications": notifications}
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"msg": "Something went wrong"}, 500
    return response, 203


@routes.route('/grouplist')
@jwt_required()
def list_groups():
    try:
        s = db_session()
        q = s.query(Group).filter(
            Group.users.any(id=get_jwt_identity())).order_by(desc(Group.id)).all()
        res = []
        for e in q:
            users = [u for u in e.users]
            name = None
            curr_user = get_user(get_jwt_identity())
            if not e.name or e.name == "":
                if len(users) < 2:  # if there is only 2 users and that the conversation doesn't have a name, we send the name of the other person to the front. I could be doing that in the front-end, now that I think about it... But you know life is full of mystery and stuff you can't control and- We'll say it's on purpose
                    if curr_user.id == users[0].id:
                        name = users[1].firstName+" "+users[1].lastName
                    else:
                        name = users[0].firstName+" "+users[0].lastName
                # If there is more than 2 users, we add all users
                else:
                    name = ", ".join(
                        [u.firstName+" "+u.lastName for u in users if curr_user.id != u.id])
            else:
                name = e.name
            res.append(
                {"name": name, "id": e.id, "picturePath": e.picturePath, "users_names": [u.firstName+" "+u.lastName for u in users]})
        s.close()
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"msg": "Something went wrong"}, 500
    return jsonify(res)


@routes.route('/messagelist', methods=['GET'])
@jwt_required()
def list_messages():
    groupId = request.args.get("groupId", None)
    try:
        s = db_session()
        group = s.query(Group).get(groupId)
        if not group:
            return {"error": "How did you get here?"}, 403
        # Checks that a user belongs to a group
        users = [e for e in s.query(Group).get(groupId).users]
        if (get_jwt_identity() not in [e.id for e in users]):
            return {"error": "User does not have access to this group"}, 403
        group_messages = s.query(Message).filter_by(
            groupId=groupId).order_by(desc(Message.time_created)).all()
        messageList = []
        mId = [m.id for m in group_messages]
        usr = s.query(User).get(get_jwt_identity())
        curr_user = get_user(get_jwt_identity())
        if not group.name or group.name == "":
            if len(users) < 2:
                if curr_user.id == users[0].id:
                    name = users[1].firstName+" "+users[1].lastName
                else:
                    name = users[0].firstName+" "+users[0].lastName
            else:
                name = ", ".join(
                    [u.firstName+" "+u.lastName for u in users if curr_user.id != u.id])
        else:
            name = group.name
        for m in group_messages:
            sender = s.query(User).get(m.author)
            try:
                if (m.id not in mId):
                    usr.messages.append(m)
                s.commit()
            except Exception as e:
                s.close()
                raise(e)
            messageList.insert(0, {
                "title": m.title,
                "content": m.content,
                "picturePath": m.picturePath,
                "sender": {
                    "firstName": sender.firstName,
                    "profilePicturePath": sender.profilePicturePath,
                    "email": sender.email
                },
                "timestamp": m.time_created})
        groupInfo = {"name": name, "picturePath": group.picturePath, "admins": [
            u.serialize for u in group.admins], "users": [u.serialize for u in group.users]}
        res = {"messages": messageList, "groupInfo": groupInfo,
               "currentUser": get_email(), "currentUserId": get_jwt_identity()}
        s.close()
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    return jsonify(res)


@routes.route('/notifications', methods=['GET'])
@jwt_required()
def list_unread_messages():
    try:
        s = db_session()
        totalUnreadMessages = s.query(Message_Seen, Message, User).filter(Message_Seen.userId == get_jwt_identity(), Message_Seen.seen == False).join(
            Message, Message_Seen.messageId == Message.id).filter(Message.author != get_jwt_identity()).join(User, User.id == Message.author).join(Group, Group.id == Message.groupId).filter(Group.users.any(id=get_jwt_identity())).order_by(Message.time_created.desc()).all()
        friendRequests = s.query(Friend).filter_by(
            friendId=get_jwt_identity(), request_pending=True).all()
        friendRequestsTotal = []
        for fr in friendRequests:
            u = s.query(User).get(fr.userId)
            friendRequestsTotal.append(
                {"firstName": u.firstName, "lastName": u.lastName, "email": u.email, "profilePicturePath": u.profilePicturePath, "id": fr.id})
        unreadMessages = []
        groupsShown = []
        for m in totalUnreadMessages:
            # gets rid of multiple messages from a single group bc idk how to do it in sqlalchemy queries
            if m[1].groupId not in groupsShown:
                group = s.query(Group).get(m[1].groupId)
                unreadMessages.append(
                    {"title": m[1].title,
                     "content": m[1].content,
                     "authorFirstName": m[2].firstName,
                     "authorLastName": m[2].lastName,
                     "authorProfilePicturePath": m[2].profilePicturePath,
                     "authorEmail": m[2].email,
                     "groupName": group.name,
                     "groupPicturePath": group.picturePath,
                     "timestamp": m[1].time_created,
                     "groupId": m[1].groupId
                     })
                groupsShown.append(m[1].groupId)
        s.close()
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    return {"messages": unreadMessages, "friendRequests": friendRequestsTotal}


@routes.route('/markallasread', methods=['GET'])
@jwt_required()
def mark_all_as_read():
    try:
        s = db_session()
        totalUnreadMessages = s.query(Message_Seen).filter_by(
            userId=get_jwt_identity(), seen=False).all()
        for m in totalUnreadMessages:
            m.seen = True
        s.commit()
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    s.close()
    return {"success": True}


# looks for a contact group convo, or creates one if it doesn't exist
@routes.route('/contactgroup', methods=['GET'])
@jwt_required()
def contact_group():
    try:
        s = db_session()
        user = get_user(get_jwt_identity())
        email = request.args.get("email", None)
        contact = s.query(User).filter_by(email=email).first()
        if not contact:
            s.close()
            return {"error": "Contact does not exist"}, 404
        contact = contact
        contact_groups = s.query(Group).filter(Group.users.any(
            id=contact.id)).filter(Group.users.any(id=get_jwt_identity())).all()
        if not contact_groups:
            contact_group = Group(
                name=None, picturePath="", users=[user, contact])
            s.add(contact_group)
            s.commit()
            contact_groups = s.query(Group).filter(Group.users.any(
                id=contact.id)).filter(Group.users.any(id=get_jwt_identity())).all()
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    res = []  # 🤮
    for e in contact_groups:
        name = None
        if e.name:
            name = e.name
        else:
            name = contact.firstName+" "+contact.lastName
        res.append({"name": name, "id": e.id, "picturePath": e.picturePath,
                   "users_names": [u.firstName for u in e.users]})
    s.close()
    return {"groups": res}


@routes.route('/story/<slug>', methods=['GET'])
def get_story(slug):
    try:
        s = db_session()
        story = s.query(Story).filter_by(slug=slug).first()
        if not story:
            return {"error": "Story does not exist"}, 404
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    s.close()
    return {"story": story.serialize}


@routes.route('/stories', methods=['GET'])
def get_stories():
    try:
        s = db_session()
        if verify_jwt_in_request(optional=True):
            userId = get_jwt_identity()
            today = datetime(datetime.today().year,
                             datetime.today().month, datetime.today().day-1)  # gets yesterday
            # stories = s.query(Story).filter(Story.author != userId, Story.time_created >= today).order_by(Story.author.desc(), Story.time_created.desc()).limit(100).all()
            stories = s.query(Story).filter(Story.author != userId).order_by(Story.author.desc(
            ), Story.time_created.desc()).limit(100).all()  # no filters by date for testing purposes because i'm really lazy
            res = [e.serialize for e in stories]
        else:
            stories = s.query(Story).order_by(
                Story.time_created.desc()).limit(100).all()
            res = [e.serialize for e in stories]
        if len(res) == 0:
            return {"error": "No stories found"}, 404
    except Exception as e:
        s.close()
        raise(e)
        return {"error": "Something went wrong"}, 500
    s.close()
    return {"stories": res}


@routes.route('/showfile/<path:path>', methods=['GET'])
def show_file(path):
    return send_from_directory('uploads', path)


@routes.route('/search', methods=['GET'])
@jwt_required()
def search():
    try:
        s = db_session()
        user = get_user(get_jwt_identity())
        firstLastNames, lastFirstNames, firstNames, lastNames, emails = [], [], [], [], []
        search_term = request.args.get("search_term", None).strip()
        if ' ' in search_term:  # in case they search for firstname and lastname
            for i in range(len(search_term.split(' '))):
                # takes the first n words as first names
                firstName = ' '.join(search_term.split(' ')[:i])
                lastName = ' '.join(search_term.split(' ')[i:])
                firstLastNames.extend(s.query(User).join(Friend, Friend.friendId == User.id).filter(Friend.userId == user.id).filter(User.firstName.ilike(
                    "%{}%".format(firstName))).filter(User.lastName.ilike("%{}%".format(lastName))).order_by(desc(User.id)).all())  # unholy abomination
                # all queries are built similarily : look for all users that are friends with the current connected user (and not necessary the other way around) bc I'm too lazy to fix it
                lastFirstNames.extend(s.query(User).join(Friend, Friend.friendId == User.id).filter(Friend.userId == user.id).filter(User.lastName.ilike("%{}%".format(
                    firstName))).filter(User.firstName.ilike("%{}%".format(lastName))).order_by(desc(User.id)).all())
        else:
            firstNames = s.query(User).join(Friend, Friend.friendId == User.id).filter(Friend.userId == user.id).filter(
                User.firstName.ilike("%{}%".format(search_term))).order_by(desc(User.id)).all()
            lastNames = s.query(User).join(Friend, Friend.friendId == User.id).filter(Friend.userId == user.id).filter(
                User.lastName.ilike("%{}%".format(search_term))).order_by(desc(User.id)).all()
            emails = s.query(User).join(Friend, Friend.friendId == User.id).filter(Friend.userId == user.id).filter(
                User.email.ilike("%{}%".format(search_term))).order_by(desc(User.id)).all()
        groupNames = s.query(Group).join(User).filter(Group.users.any(id=get_jwt_identity())).filter(
            Group.name.ilike("%{}%".format(search_term))).order_by(desc(Group.id)).all()
        if " " in search_term:
            search_terms = search_term.split(" ")
        else:
            search_terms = [search_term]
        allGroupUserNames = []
        for e in search_terms:
            allGroupUserNames.append(s.query(Group).join(User).filter(Group.users.any(id=get_jwt_identity())).filter(
                or_(
                    Group.users.any(
                        User.firstName.ilike("%{}%".format(e))),
                    Group.users.any(
                        User.lastName.ilike("%{}%".format(e)))
                )).order_by(desc(Group.id)).all())
        for groupUserNames in allGroupUserNames:
            for grp in groupUserNames:
                # we ignore groups with no name bc they imply 1 to 1 convo and we already find those through the user filter
                if groupUserNames not in groupNames and grp.name and grp.name != "":
                    groupNames.append(grp)
        res = dict()
        res["users"] = []
        res['isFirstLastName'] = False
        res['isLastFirstNames'] = False
        # monstrosity that gets rid of duplicates
        for resultBit in [firstLastNames, lastFirstNames, firstNames, lastNames, emails]:
            if resultBit and len(resultBit) > 0:
                for r in resultBit:
                    isIn = False
                    for e in res['users']:
                        if e['email'] == r.email:
                            isIn = True
                    if not isIn:
                        groupForUser = s.query(Group).filter(Group.name == None).filter(
                            and_(Group.users.any(id=get_jwt_identity()), Group.users.any(id=r.id))).first()
                        minires = r.serialize
                        minires['groupId'] = groupForUser.id
                        res['users'].append(minires)
        if groupNames:
            res["groupNames"] = [e.serialize for e in groupNames]
        s.close()
        if not res or res == {} or len(res) == 0:
            return {"error": "No results found"}, 404
    except Exception as e:
        s.close()
        raise(e)
        return {"error": "Something went wrong"}, 500
    s.close()
    return {"results": res}


# ================== POST ====================
@routes.route('/signup', methods=['POST'])
def create_user():
    try:
        s = db_session()
        firstName = request.form.get("firstName", None)
        lastName = request.form.get("lastName", None)
        email = request.form.get("email", None)
        userExists = s.query(User).filter_by(email=email).first()
        if userExists:
            s.close()
            return {"error": "This email address is already in use", "errorToSet": "email"}, 403
        if not firstName or not isValidStr(firstName):
            s.close()
            return {"error": "First name is invalid", "errorToSet": "firstName"}, 403
        if not lastName or not isValidStr(lastName):
            return {"error": "Last name is invalid", "errorToSet": "lastName"}, 403
        if 'file' not in request.files or not request.files['file'] or not allowed_file(request.files['file'].filename, current_app.config['ALLOWED_EXTENSIONS']):
            url_name = None
        else:
            filename = secure_filename(request.files['file'].filename)
            try:
                request.files['file'].save(os.path.join(
                    current_app.config['UPLOAD_FOLDER'], filename))
                # hacky, just for local management
                url_name = current_app.config['SERVER_LOC'] + \
                    "api/showfile/"+filename
            except:
                return {"error": "Image could not be uploaded properly", "errorToSet": "Image"}, 500
        password1 = request.form.get("password1", None)
        password2 = request.form.get("password2", None)
        if password1 != password2:
            return {"error": "Passwords don't match!"}, 403
        gender = request.form.get("gender", None)
        if gender and gender not in ["Female", "Male", "Non-binary", "Other", "Prefer not to say"]:
            # you might be wondering why I'm using \" instead of ` so much, well the truth is that-
            return {"error": "Gender collection here is only used for demographic statistical studies. Please use one of the genders listed in the field. If none fits your current gender, chose \"Other\".", "errorToSet": "gender"}, 403

        isAdmin = False
        if not email or not isEmail(email):
            s.close()
            return {"error": "Email is invalid", "errorToSet": "email"}, 403

        if not isSafe(password1):
            s.close()
            return {"error": "Password isn't safe", "errorToSet": "password"}, 403
        salt = bcrypt.gensalt()
        password = bcrypt.hashpw(password=str.encode(
            password1, 'utf-8'), salt=salt)
        userSalt = UserSalt(email=email, salt=salt)
        user = User(firstName=firstName.strip(), lastName=lastName.strip(), email=email, password=password,
                    gender=gender, isAdmin=isAdmin, profilePicturePath=url_name)
        s.add(userSalt)
        s.add(user)
        s.commit()
        s.close()
    except Exception as e:
        if not TESTING:
            pass
        else:
            raise(e)
        s.close()
        return {"error": "User creation could not proceed. Something went wrong on our end."}, 500
    return {"success": True}, 203


@routes.route('/addUser', methods=['POST'])
@jwt_required()
def addUser():
    try:
        s = db_session()
        user = s.query(User).get(get_jwt_identity())
        email = request.json.get("email", None)
        if not email:
            return {"error": "No email provided"}, 403
        if not isEmail(email) or user.email == email:
            return {"error": "Error. Please enter a valid email"}, 403
        userToAdd = s.query(User).filter(User.email == email).first()
        if not userToAdd:
            return {"error": "User not found"}, 404
        if userToAdd in user.friends:
            return {"error": "User already in friends list"}, 403
        friendship = Friend(
            userId=user.id, friendId=userToAdd.id, request_pending=True)
        s.add(friendship)
        group = Group(name=None, picturePath=None, creator=None,
                      admins=[user, userToAdd], users=[user, userToAdd])
        s.add(group)
        s.commit()
        s.close()
    except Exception as e:
        if not TESTING:
            pass
        else:
            raise(e)
        s.close()
        return {"error": "Something went wrong"}, 500
    return {"message": "User was successfully added. They will get a request that they will have to accept before you can start communicating with them."}, 203


@routes.route('/setFriendRequest', methods=['POST'])
@jwt_required()
def setFriendRequest():
    try:
        s = db_session()
        friendShipId = request.json.get("friendshipId", None)
        status = request.json.get("status", None)
        if friendShipId != None and status != None:
            friendship = s.query(Friend).get(friendShipId)
            friendship.request_pending = False
            if status:
                reciprocal_friendship = Friend(userId=get_jwt_identity(
                ), friendId=friendship.userId, request_pending=False)
                s.add(reciprocal_friendship)
            s.commit()
        else:
            raise Exception(
                "An unexpected error occurred. Please reload the page and try again.")
    except Exception as e:
        if not TESTING:
            pass
        else:
            raise(e)
        s.close()
        return {"error": "Something went wrong"}, 500
    return {"success": True}, 203


@routes.route('/createGroup', methods=['POST'])
@jwt_required()
def create_group():
    try:
        s = db_session()
        user = get_user(get_jwt_identity())
        emailList = request.form.get("emailList", None).split(",")
        if len(emailList) > 3:
            s.close()
            return {"error", "Not enough viable members in the group"}, 400
        name = request.form.get('groupName', None)
        if 'file' not in request.files or not request.files['file'] or not allowed_file(request.files['file'].filename, current_app.config['ALLOWED_EXTENSIONS']):
            url_name = None
        else:
            filename = secure_filename(request.files['file'].filename)
            try:
                request.files['file'].save(os.path.join(
                    current_app.config['UPLOAD_FOLDER'], filename))
                # hacky, just for local management
                url_name = current_app.config['SERVER_LOC'] + \
                    "api/showfile/"+filename
            except:
                s.close()
                return {"error": "Image could not be uploaded properly"}, 500
        if not name or name.strip() == "":
            s.close()
            return {"error", "Group name unauthorized"}, 400
        users = []
        for email in emailList:
            u = s.query(User).filter_by(email=email.strip()).first()
            if u:
                users.append(u)
            else:
                pass  # TODO: send an email to people who are not registered in the app?
        # users = list(set(users)) # yeet dupes
        newUsers = []
        for u in users:  # safer way to yeet dupes
            for e in newUsers:
                if u.id == e.id or u.id == get_jwt_identity():  # can't add yourself, duh
                    break
            else:  # evil warlock trick
                newUsers.append(u)
        newUsers.append(user)
        group = Group(name=name, picturePath=url_name,
                      users=newUsers, admins=[user], creator=user.id)
        s.add(group)
        s.commit()
        lastrowid = group.id
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    s.close()
    return {"success": True, "roomId": lastrowid}, 203

# =================== PUT =====================


@routes.route('/editProfile', methods=['PUT'])
@jwt_required()
def edit_profile():
    user = None
    try:
        s = db_session()
        email = request.form.get("email", None)
        firstName = request.form.get("firstName", None)
        lastName = request.form.get("lastName", None)

        password = request.form.get("password", None)

        if not password:
            s.close()
            return {"error": "Fill password to save edits.", "errorToSet": "password"}, 403

        gender = request.form.get("gender", None)
        if gender == "none":
            gender = None
        if gender and gender not in ["Female", "Male", "Non-binary", "Other", "Prefer not to say"]:
            s.close()
            return {"error": "Gender collection here is only used for demographic statistical studies. Please use one of the genders listed in the field. If none fits your current gender, chose \"Other\".", "errorToSet": "gender", "errorToSet": "gender"}, 403

        if 'file' not in request.files or not request.files['file'] or not allowed_file(request.files['file'].filename, current_app.config['ALLOWED_EXTENSIONS']):
            url_name = None
        else:
            filename = secure_filename(request.files['file'].filename)
            try:
                request.files['file'].save(os.path.join(
                    current_app.config['UPLOAD_FOLDER'], filename))
                # hacky, just for local management
                url_name = current_app.config['SERVER_LOC'] + \
                    "api/showfile/"+filename
            except:
                return {"error": "Image could not be uploaded properly", "errorToSet": "Image"}, 500

        user = s.query(User).filter_by(
            id=get_jwt_identity()).first()

        if user.email == email and user.firstName == firstName and user.lastName == lastName and user.gender == gender and not url_name:
            s.close()
            return {"error": "No information was provided."}, 204

        userTry = s.query(UserSalt).filter_by(email=user.email).first()
        if not userTry:
            return {"error": "Wrong email, somehow?", "fieldToSet": "email"}, 403
        salt = userTry.salt
        userPwd = s.query(User).filter_by(
            email=user.email, password=bcrypt.hashpw(password=str.encode(password, 'utf-8'), salt=salt)).first()

        if not userPwd:
            s.close()
            return {"error": "Password is incorrect.", "errorToSet": "password"}, 403

        if gender:
            user.gender = gender

        if email:
            # redundant, I know. But the first call to the salts seems to glitch out somehow?
            usrHash = s.query(UserSalt).filter_by(email=user.email).first()

            user.email = email
            usrHash.email = email

        if url_name:
            user.profilePicturePath = url_name

        if firstName:
            user.firstName = firstName

        if lastName:
            user.lastName = lastName
        s.commit()
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    finally:
        if user:
            finalUser = user.serialize
        else:
            finalUser = s.query(User).get(get_jwt_identity())
    s.close()
    return {"success": True, "userInfo": finalUser}


@routes.route('/editGroup', methods=['PUT'])
@jwt_required()
def edit_group():
    grpFinal = []
    try:
        s = db_session()
        user = get_user(get_jwt_identity())
        groupId = request.json.get('groupId', None)
        users = request.json.get('users', None)
        admins = request.json.get('admins', None)
        users = list(set([e['email'] for e in users]))
        admins = list(set([a['email'] for a in admins]))
        groupName = request.json.get('groupName', None)
        if not groupName or not isValidStr(groupName):
            s.close()
            return {"error": "Group name is invalid", "errorToSet": "groupName"}, 403
        if len(users) < 2:
            s.close()
            return {"error": "Too few users.", "errorToSet": "participants"}, 403
        group = s.query(Group).filter_by(id=groupId).filter(
            Group.admins.any(id=get_jwt_identity())).first()
        if not group:
            s.close()
            return {"error": "You don't have access to this group.", "errorToSet": "admins"}, 403
        usersChecked = []
        for uid in users:  # checks users before doing anything stupid
            if type(uid) is str and not uid.strip().isdecimal():
                tUser = s.query(User).filter_by(email=uid.strip()).first()
            else:  # will need to change to account for non-registered users in the future
                tUser = s.query(User).filter_by(id=uid).first()
            if not tUser:  # can be deleted safely, as wrong users won't get added
                s.close()
                return {"error": "One of the given users is invalid.", "errorToSet": "participants"}, 403
            if uid != get_jwt_identity():
                usersChecked.append(tUser)
        newUsers = []
        listIdClean = []
        for u in usersChecked:
            for e in newUsers:
                if u.id == e.id or u.id == get_jwt_identity():
                    break
            else:
                newUsers.append(u)
                listIdClean.append(u.id)
        finalAdmins = []
        for a in admins:
            admin = s.query(User).filter_by(email=a).first()
            if not admin:
                return {"error": "One of the given admins seems to be invalid", "errorToSet": "admins"}, 403
            if admin.id != get_jwt_identity():
                if admin.id in listIdClean:  # we safely add the user back to the admins at the end
                    finalAdmins.append(admin)
                else:
                    return {"error": "One of the given admins doesn't belong to the group.", "errorToSet": "admins"}, 403

        finalAdmins.append(user)
        group.admins = finalAdmins
        newUsers.append(user)
        group.users = newUsers
        finalUsers = newUsers
        group.name = groupName
        grpFinal = {"name": group.name, "picturePath": group.picturePath, "admins": [u.serialize for u in group.admins], "users": [
            u.serialize for u in group.users]}
        s.commit()
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    s.close()
    return {"success": True, "groupInfo": grpFinal}


# ================== PATCH ====================

@routes.route('/leaveGroup', methods=['PATCH'])
@jwt_required()
def leave_group():
    try:
        s = db_session()
        user = get_user(get_jwt_identity())
        groupId = request.json.get('groupId', None)
        group = s.query(Group).filter_by(id=groupId).filter(
            Group.users.any(id=get_jwt_identity())).first()
        if not group or len(group.users)<3:
            s.close()
            return {"error": "You can't access this ressource."}, 403
        group.users.remove(user)
        try:  # don't exactly know how to make a simple if for that
            group.admins.remove(user)
        except:
            pass
        s.commit()
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    s.close()
    return {"success": True}

# ================== DELETE ====================


@routes.route('/deleteGroup', methods=['DELETE'])
@jwt_required()
def delete_group():
    print('trying to delete?')
    try:
        s = db_session()
        user = get_user(get_jwt_identity())
        groupId = request.json.get('groupId', None)
        group = s.query(Group).filter(
            Group.admins.any(id=get_jwt_identity())).filter_by(id=groupId).first()
        if group.name and group.name != "" and len(group.users) != 2:
            s.close()
            # design choice
            return {"error": "Can't delete 1 on 1 conversations."}, 403
        if not group:
            s.close()
            return {"error": "You can't access this ressource."}, 403
        try:
            group.users = []  # seems like cascade isn't working properly here...?
            group.admins = []  # same thing
            s.delete(group)
        except Exception as e:
            raise (e)
            return {"error": "Something went wrong during deletion. Try reloading the page."}, 500
        s.commit()
        print('DELETED')
    except Exception as e:
        s.close()
        if not TESTING:
            pass
        else:
            raise(e)
        return {"error": "Something went wrong"}, 500
    s.close()
    return {"success": True}
