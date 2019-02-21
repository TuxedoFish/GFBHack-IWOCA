from wk_client import models, db


def nuke_database():
    """ Delete all objects"""
    for cf in models.CashFlow.query.all():
        db.session.delete(cf)
    for l in models.Loan.query.all():
        db.session.delete(l)
    for dec in models.Decision.query.all():
        db.session.delete(dec)
    for u in models.User.query.all():
        db.session.delete(u)

    db.session.commit()
