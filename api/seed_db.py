import time
import os
import sys
from init_db import initdb
from drop_all import dropdb
from time import sleep
from random import randrange
from database import db_session, Base, engine
from faker import Faker
import models
fake = Faker()
dropdb()
initdb()


def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\n"):
    """
    Making this work in powershell was stupidly and needlessly convoluted...
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 *
                                                     (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    if sys.platform == "win32" or sys.platform == "win64":
        sys.stdout.write(f'{prefix} |{bar}| {percent}% {suffix}')
        sys.stdout.flush()
        sys.stdout.write('\r')
        sys.stdout.flush()
    else:
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    if iteration == total:
        print()


def generate_emails(amt=10):
    emails = []
    while len(set(emails)) < amt:
        email = fake.email()
        if email not in emails:
            emails.append(email)
    return list(set(emails))


def generate_users(amt=10):
    users = []
    emails = generate_emails(amt)
    printProgressBar(0, amt, prefix='Generating users...', suffix='Done!', length=50)
    for i in range(amt):
        isAdmin = False
        if randrange(100) == 0:
            isAdmin = True
        users.append(models.User(
            firstName=fake.first_name(),
            lastName=fake.last_name(),
            email=emails[i],
            password=fake.password(),
            isAdmin=isAdmin,
            profilePicturePath=fake.image_url(),
        ))
        printProgressBar(i + 1, amt, prefix='Generating users...',
                         suffix='Done!', length=50)
    return users


def generate_groups(s, amt=10):
    groups = []
    userGroups = []
    insertedId = []
    printProgressBar(0, amt, prefix='Generating groups...', suffix='Done!', length=50)
    for i in range(amt):
        adminId = randrange(amt)+1
        participants = []
        randParticipant = adminId
        participantsId = [adminId]
        groupSize = randrange(10)+1
        for j in range(groupSize+1):
            if randParticipant not in participantsId:
                participants.append(randParticipant)
            participantsId.append(randParticipant)
            randParticipant = randrange(amt)+1
        if groupSize == 1:
            if len(participants) > 0 and participants[0] != None:
                tempParticipant = s.query(models.User).get(participants[0])
                groupName = tempParticipant.firstName+" "+tempParticipant.lastName
        groupName = " ".join(fake.words(randrange(6)+1))
        finalParticipants = []
        for n in participants:
            finalParticipants.append(s.query(models.User).get(n))
        insertedId.append(i+1)
        groups.append(models.Group(
            id=i+1,
            name=groupName,
            picturePath=fake.image_url(),
            groupAdmin=adminId,
            users=finalParticipants
        ))
        printProgressBar(i + 1, amt, prefix='Generating groups...',
                         suffix='Done!', length=50)
    return groups


def generate_friends(s, amt=10):
    friends = []
    printProgressBar(0, amt, prefix='Generating friends...', suffix='Done!', length=50)
    for i in range(amt):
        randomFriends = []
        for j in range(10):
            randomFriend = randrange(amt)+1
            while randomFriend != i+1 and randomFriend in randomFriends:
                randomFriend = randrange(amt)+1
            randomFriends.append(randomFriend)
            friends.append(models.Friend(
                userId=i+1,
                friendId=randomFriends[j]
            ))
        printProgressBar(i + 1, amt, prefix='Generating friends...',
                         suffix='Done!', length=50)
    return friends


def generate_messages(s, amt=10):
    messages = []
    printProgressBar(0, amt, prefix='Generating messages (this might take a while)...', suffix='Done!', length=50)
    for i in range(amt):
        ppath = None
        group = s.query(models.Group).get(i+1)
        if group:
            for j in range(randrange(int(amt/10))+1):
                author = group.getusers()[randrange(len(group.getusers()))].id
                if randrange(amt) == 0:
                    ppath = fake.image_url(),
                messages.append(models.Message(
                    title=" ".join(fake.words(randrange(6)+1)),
                    content=fake.text(max_nb_chars=randrange(250) +
                                      5),  # very arbitrary, I know
                    picturePath=ppath,
                    author=author,
                    groupId=group.id))
            printProgressBar(i + 1, amt, prefix='Generating messages (this might take a while)...',
                             suffix='Done!', length=50)
    return messages


def seed_db():
    # I have to commit after generating each separate table data because otherwise I can't seem to be able to create groups. Also, groups seem to be able to insert themselves without having to use bulk_save_objects ...?
    s = db_session()
    s.bulk_save_objects(generate_users(1000))
    s.commit()
    s.bulk_save_objects(generate_friends(s, 1000))
    s.commit()
    groups = generate_groups(s, 1000)
    s.commit()
    s.bulk_save_objects(generate_messages(s, 1000))
    s.commit()


seed_db()
