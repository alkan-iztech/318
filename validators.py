import re

def validate_password(pswd, pswd_cnfrm=None):
    if (len(pswd) < 5):
        return 'Password must be at least 5 characters'
    elif (len(pswd) > 20):
        return 'Passwrod must be max of 50 characters'
    elif (pswd_cnfrm != None and pswd != pswd_cnfrm):
        return 'Passwords do not match'
    else:
        return True

def validate_user_data(db, User, username, email, password, password_confirm):
    if (len(username) == 0 or len(username) > 20):
        return 'Username must be 1-20 characters'
    if not (re.match(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+', email)):
        return 'Please enter a valid email'
    if db.session.query(User).filter(User.username == username).count() > 0:
        return 'This username is already registerd'
    if db.session.query(User).filter(User.email == email).count() > 0:
        return 'This email is already registered'
    pswd_validation = validate_password(password, password_confirm)
    if (pswd_validation != True):
        return pswd_validation
    return ''
