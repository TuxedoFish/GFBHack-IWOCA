import datetime


def get_repayment_amount(amount, duration_days, repayment_frequency_days, interest_daily, x_guess=None):
    def residual(x, amount, duration_days, repayment_frequency_days, interest_daily):
        for i in range(1, duration_days + 1):
            amount *= 1+interest_daily
            if i%repayment_frequency_days == 0:
                amount -= x
        return amount
    x_guess = x_guess or amount / duration_days * repayment_frequency_days
    x, res = fake_newton_rhapson(x_guess, lambda x: residual(x, amount, duration_days, repayment_frequency_days, interest_daily))
    return x, res


def fake_newton_rhapson(x, fun):
    # TODO: Replace with the real thing.
    epsilon = 1e-5
    res = fun(x)
    dx = fun(x+epsilon) - fun(x-epsilon)
    x_try = x
    for _ in range(50):
        f = res/dx
        x_try = x_try - epsilon * f
        res = fun(x_try)
        dx = fun(x_try+epsilon) - fun(x_try - epsilon)
    return x_try, res


def shifted(days, hours, dt=None):
    dt = dt or time_now()
    return dt + datetime.timedelta(days=days, hours=hours)


def time_now():
    return datetime.datetime.now()


def get_date(x):
    if isinstance(x, datetime.datetime):
        return x.date()
    elif isinstance(x, datetime.date):
        return x
    elif isinstance(x, int):
        return x
    else:
        raise TypeError
