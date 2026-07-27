import csv

def makeAvatarIdP(age, gender):
    if(age<=19):
        if(gender == "male"):
            avatarId = "fifth"
        elif(gender == "female"):
            avatarId = "sixth"
        else:
            avatarId = "first"
    elif(age>19 and age<=60):
        if(gender == "male"):
            avatarId = "second"
        elif(gender == "female"):
            avatarId = "first"
        else:
            avatarId = "first"
    elif(age>60):
        if(gender == "male"):
            avatarId = "third"
        elif(gender == "female"):
            avatarId = "fourth"
        else:
            avatarId = "first"
    return avatarId

def loadBmiData(filePath):
    with open(filePath, newline="") as f:     #new line makes sure that python dont remove the newline formats and make sure that csv will take care of it as csv will
        reader = csv.DictReader(filePath)  #makes the dictonary for each row map the col with that value and reader is a pointer so down with iterate through all rows
    result = []  #reader is still not a list its an object of csv whidch maps to dict
    for row in reader:
        reader.append({
            "Month": int(row["Month"]),
            "P5": float(row["P5"]),
            "P85": float(row["P85"]),
            "P95": float(row["P95"])
        })
    return result

class APIException(Exception):  #so this we make APIException and exception
    def __init__(self, code, detail, statusCode):
        self.statusCode = statusCode
        self.code = code
        self.detail = detail
