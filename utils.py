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